from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.deps import get_db_session, get_es
from app.retrieval.core.chunk_service import ChunkService
from app.retrieval.core.directory_service import DirectoryService
from app.retrieval.core.document_service import DocumentService
from app.retrieval.repositories.chunk_repository import ChunkRepository
from app.retrieval.repositories.directory_repository import DirectoryRepository
from app.retrieval.repositories.document_repository import DocumentRepository

Session = Annotated[AsyncSession, Depends(get_db_session)]


def get_directory_service(session: Session) -> DirectoryService:
    return DirectoryService(session, DirectoryRepository(session))


def get_document_service(session: Session) -> DocumentService:
    return DocumentService(session, DocumentRepository(session), DirectoryRepository(session))


def get_chunk_service(
    session: Session,
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChunkService:
    return ChunkService(ChunkRepository(es, settings.es_chunks_index), DocumentRepository(session))
