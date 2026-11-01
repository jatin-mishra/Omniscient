from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.deps import get_db_session, get_es
from app.retrieval.repositories.chunk_search_repository import ChunkSearchRepository
from app.retrieval.repositories.document_repository import DocumentRepository


def get_document_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentRepository:
    return DocumentRepository(session)


def get_chunk_search_repo(
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChunkSearchRepository:
    return ChunkSearchRepository(es, settings.es_chunks_index)
