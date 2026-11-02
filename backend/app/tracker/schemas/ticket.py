from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.tracker.models import (
    DocumentType,
    ProviderName,
    Ticket,
    TicketPriority,
    TicketStatus,
    TicketType,
)

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(max_length=2000)]


class StrictModel(BaseModel):
    """Request base: unknown fields are a 422, so a typo is never silently ignored."""

    model_config = ConfigDict(extra="forbid")


class TicketCreate(StrictModel):
    document_type: DocumentType
    document_id: UUID
    provider: ProviderName = ProviderName.INTERNAL
    type: TicketType
    title: Title
    description: Description | None = None
    priority: TicketPriority
    assignee_id: UUID | None = None
    reporter_id: UUID | None = None  # defaults to the caller
    due_at: AwareDatetime | None = None


class TicketResponse(BaseModel):
    id: UUID
    document_type: DocumentType
    document_id: UUID
    provider: ProviderName
    external_ticket_id: str
    type: TicketType
    title: str
    description: str | None
    priority: TicketPriority
    status: TicketStatus
    assignee_id: UUID | None
    reporter_id: UUID
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
    resolved_at: datetime | None
    due_at: datetime | None

    @classmethod
    def from_model(cls, ticket: Ticket) -> Self:
        return cls(
            id=ticket.external_id,
            document_type=ticket.document_type,
            document_id=ticket.document_id,
            provider=ticket.provider,
            external_ticket_id=ticket.external_ticket_id,
            type=ticket.type,
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            status=ticket.status,
            assignee_id=ticket.assignee_id,
            reporter_id=ticket.reporter_id,
            created_at=ticket.created_at,
            created_by=ticket.created_by,
            updated_at=ticket.updated_at,
            updated_by=ticket.updated_by,
            resolved_at=ticket.resolved_at,
            due_at=ticket.due_at,
        )
