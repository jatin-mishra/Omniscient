from collections.abc import AsyncIterator

from elasticsearch import AsyncElasticsearch
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.engine
    return engine


def get_es(request: Request) -> AsyncElasticsearch:
    es: AsyncElasticsearch = request.app.state.es
    return es


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request. The caller commits; anything uncommitted is rolled back on close."""
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session
