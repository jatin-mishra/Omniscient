import asyncio
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.deps import get_engine, get_es
from app.core.config import Settings, get_settings
from app.db import postgres
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


@router.get("/health/ready")
async def readiness(
    response: Response,
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
) -> ReadinessResponse:
    is_postgres_up, is_es_up = await asyncio.gather(postgres.ping_postgres(engine), es.ping())
    checks = {"postgres": is_postgres_up, "elasticsearch": is_es_up}
    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ready" if is_ready else "not_ready", checks=checks)
