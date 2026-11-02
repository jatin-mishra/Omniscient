import logging

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.db.base import Base

log = logging.getLogger(__name__)


def create_db(settings: Settings) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build the engine and session factory. No connection is opened until first use."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except DBAPIError as exc:
            raise RuntimeError(
                "pgvector extension is unavailable: run Postgres from the pgvector/pgvector image"
            ) from exc
        await conn.run_sync(Base.metadata.create_all)


async def ping_postgres(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        log.warning("postgres ping failed: %s", exc)
        return False
    return True
