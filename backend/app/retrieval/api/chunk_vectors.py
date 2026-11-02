from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.retrieval.core.chunk_vector_service import ChunkVectorService
from app.retrieval.deps import get_chunk_vector_service
from app.retrieval.schemas.chunk_vector import ChunkVectorCreate, ChunkVectorResponse

router = APIRouter(prefix="/chunk-vectors", tags=["chunk-vectors"])

Service = Annotated[ChunkVectorService, Depends(get_chunk_vector_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_chunk_vector(
    body: ChunkVectorCreate, service: Service, actor: Actor
) -> ChunkVectorResponse:
    return await service.add(body, actor)
