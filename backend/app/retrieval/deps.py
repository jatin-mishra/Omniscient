from datetime import timedelta
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.config import Settings, get_settings
from app.db.deps import get_db_session, get_es
from app.retrieval.core.chunk_service import ChunkService
from app.retrieval.core.chunk_vector_service import ChunkVectorService
from app.retrieval.core.directory_service import DirectoryService
from app.retrieval.core.document_service import DocumentService
from app.retrieval.core.embedding import get_embedding_provider
from app.retrieval.core.workflow_service import WorkflowService
from app.retrieval.repositories.chunk_repository import ChunkRepository
from app.retrieval.repositories.chunk_vector_repository import ChunkVectorRepository
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


def get_chunk_vector_service(
    session: Session, settings: Annotated[Settings, Depends(get_settings)]
) -> ChunkVectorService:
    return ChunkVectorService(
        session,
        ChunkVectorRepository(session),
        DocumentRepository(session),
        get_embedding_provider(settings.embedding_provider, settings.embedding_dimensions),
        settings.embedding_dimensions,
    )


def get_temporal_client(request: Request) -> Client:
    client: Client = request.app.state.temporal
    return client


def get_workflow_service(
    client: Annotated[Client, Depends(get_temporal_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowService:
    return WorkflowService(
        client,
        settings.temporal_task_queue,
        timedelta(seconds=settings.workflow_execution_timeout_s),
        timedelta(seconds=settings.temporal_rpc_timeout_s),
    )
