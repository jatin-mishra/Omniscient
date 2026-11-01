from collections.abc import AsyncIterator
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.repositories.chunk_search_repository import ChunkSearchRepository
from app.repositories.document_repository import DocumentRepository


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


def get_document_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


def get_chunk_search_repo(
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChunkSearchRepository:
    return ChunkSearchRepository(es, settings.es_chunks_index)
