from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth import get_actor
from app.tracker.core.ticket_service import TicketService
from app.tracker.deps import get_ticket_service
from app.tracker.models import DocumentType
from app.tracker.schemas.ticket import TicketCreate, TicketResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])

Service = Annotated[TicketService, Depends(get_ticket_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket(body: TicketCreate, service: Service, actor: Actor) -> TicketResponse:
    return await service.create(body, actor)


@router.get("")
async def list_tickets(
    document_type: DocumentType, document_id: UUID, service: Service, actor: Actor
) -> Sequence[TicketResponse]:
    return await service.list_for_document(document_type, document_id)


@router.post("/webhooks/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def status_webhook(provider: str, request: Request, service: Service) -> Response:
    """Called by the ticket system, not a user: authenticated by the provider's signature."""
    await service.handle_status_webhook(provider, request.headers, await request.body())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
