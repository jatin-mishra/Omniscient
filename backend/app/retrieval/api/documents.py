from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.retrieval.core.document_service import DocumentService
from app.retrieval.deps import get_document_service
from app.retrieval.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])

Service = Annotated[DocumentService, Depends(get_document_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(body: DocumentCreate, service: Service, actor: Actor) -> DocumentResponse:
    return await service.create(body, actor)


@router.patch("/{document_id}")
async def update_document(
    document_id: UUID, body: DocumentUpdate, service: Service, actor: Actor
) -> DocumentResponse:
    return await service.update(document_id, body, actor)
