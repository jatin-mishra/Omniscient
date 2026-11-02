from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin
from app.tracker.models.enums import (
    RESOLVED_STATUSES,
    DocumentType,
    ProviderName,
    TicketPriority,
    TicketStatus,
    TicketType,
)


def _enum[E: StrEnum](cls: type[E]) -> Enum:
    # Lowercase values (rca), not member names (RCA), so rows match the API.
    # VARCHAR + CHECK instead of a native PG enum: adding a value later needs no ALTER TYPE.
    return Enum(
        cls,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )


class Ticket(IdMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("provider", "external_ticket_id", name="uq_tickets_provider_ticket"),
        Index("ix_tickets_document", "document_type", "document_id"),
    )

    # The document is owned by another module, so a plain UUID with no FK
    document_type: Mapped[DocumentType] = mapped_column(_enum(DocumentType))
    document_id: Mapped[UUID] = mapped_column()

    provider: Mapped[ProviderName] = mapped_column(_enum(ProviderName))
    external_ticket_id: Mapped[str] = mapped_column(String(128))

    type: Mapped[TicketType] = mapped_column(_enum(TicketType))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[TicketPriority] = mapped_column(_enum(TicketPriority))
    status: Mapped[TicketStatus] = mapped_column(_enum(TicketStatus), default=TicketStatus.OPEN)

    # Users are owned by onboarding: plain UUIDs, no FK
    assignee_id: Mapped[UUID | None] = mapped_column()
    reporter_id: Mapped[UUID] = mapped_column()

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When the provider says the last applied status event happened (stale-event guard)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def apply_status_event(self, status: TicketStatus, occurred_at: datetime, actor: UUID) -> bool:
        """Applies a provider status event. Returns False when it is older than the last
        applied one (ignored). The same status again only moves the event clock."""
        if self.last_event_at is not None and occurred_at < self.last_event_at:
            return False
        self.last_event_at = occurred_at
        if status is not self.status:
            self.status = status
            self.updated_by = actor
            if status not in RESOLVED_STATUSES:
                self.resolved_at = None
            elif self.resolved_at is None:
                self.resolved_at = occurred_at
        return True
