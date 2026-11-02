from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.retrieval.core.chunk_service import ChunkService
from app.retrieval.deps import get_chunk_service
from app.retrieval.schemas.chunk import ChunkCreate, ChunkResponse, ChunkUpdate

router = APIRouter(prefix="/documents/{document_id}/chunks", tags=["chunks"])

Service = Annotated[ChunkService, Depends(get_chunk_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_chunk(
    document_id: UUID, body: ChunkCreate, service: Service, actor: Actor
) -> ChunkResponse:
    return await service.add(document_id, body, actor)


@router.patch("/{chunk_id}")
async def update_chunk(
    document_id: UUID, chunk_id: str, body: ChunkUpdate, service: Service, actor: Actor
) -> ChunkResponse:
    return await service.update(document_id, chunk_id, body, actor)
