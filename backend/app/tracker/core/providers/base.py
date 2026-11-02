from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.errors import AppError
from app.tracker.models import (
    DocumentType,
    ProviderName,
    TicketPriority,
    TicketStatus,
    TicketType,
)


class ProviderError(AppError):
    status_code = 502
    code = "ticket_provider_error"


@dataclass(frozen=True)
class TicketSpec:
    document_type: DocumentType
    document_id: UUID
    type: TicketType
    title: str
    description: str | None
    priority: TicketPriority
    assignee_id: UUID | None
    reporter_id: UUID
    due_at: datetime | None


@dataclass(frozen=True)
class ExternalTicket:
    external_ticket_id: str
    status: TicketStatus


@dataclass(frozen=True)
class StatusEvent:
    external_ticket_id: str
    status: TicketStatus
    occurred_at: datetime


class TicketProvider(Protocol):
    """A ticket system (internal today, Jira later). Everything provider-specific lives here:
    creating the ticket, and authenticating + decoding that system's status webhook."""

    name: ProviderName

    async def create_ticket(self, spec: TicketSpec) -> ExternalTicket: ...

    def parse_status_event(self, headers: Mapping[str, str], body: bytes) -> StatusEvent:
        """Verifies the webhook is genuine (UnauthorizedError) and decodes it
        (InvalidRequestError when malformed)."""
        ...
