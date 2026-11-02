from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.retrieval.core.directory_service import DirectoryService
from app.retrieval.deps import get_directory_service
from app.retrieval.schemas.directory import DirectoryCreate, DirectoryResponse, DirectoryUpdate

router = APIRouter(prefix="/directories", tags=["directories"])

Service = Annotated[DirectoryService, Depends(get_directory_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_directory(
    body: DirectoryCreate, service: Service, actor: Actor
) -> DirectoryResponse:
    return await service.create(body, actor)


@router.patch("/{directory_id}")
async def update_directory(
    directory_id: UUID, body: DirectoryUpdate, service: Service, actor: Actor
) -> DirectoryResponse:
    return await service.update(directory_id, body, actor)
