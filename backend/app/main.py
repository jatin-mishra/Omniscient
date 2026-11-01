import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.elastic import create_es_client
from app.db.postgres import create_db, create_tables
from app.errors import register_exception_handlers
from app.logging import configure_logging
from app.middlewares.request_id import RequestIdMiddleware
from app.onboarding import models as onboarding_models  # noqa: F401  registers tables
from app.retrieval import models as retrieval_models  # noqa: F401  registers tables
from app.retrieval.models.chunk import ensure_chunk_index
from app.router import api_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("starting %s (%s)", settings.app_name, settings.environment)
    app.state.engine, app.state.sessionmaker = create_db(settings)
    app.state.es = create_es_client(settings)
    try:
        if settings.create_schema_on_startup:
            await create_tables(app.state.engine)
            await ensure_chunk_index(app.state.es, settings.es_chunks_index)
            log.info("storage ready: tables created, index %s", settings.es_chunks_index)
        yield
    finally:
        await app.state.es.close()
        await app.state.engine.dispose()
        log.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
