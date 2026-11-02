from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.db.repository import Repository
from app.tracker.models import DocumentType, ProviderName, Ticket


class TicketRepository(Repository[Ticket]):
    model = Ticket

    async def list_for_document(
        self, document_type: DocumentType, document_id: UUID
    ) -> Sequence[Ticket]:
        stmt = (
            select(Ticket)
            .where(Ticket.document_type == document_type, Ticket.document_id == document_id)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        )
        return (await self._session.scalars(stmt)).all()

    async def find_by_provider_ticket(
        self, provider: ProviderName, external_ticket_id: str
    ) -> Ticket | None:
        stmt = select(Ticket).where(
            Ticket.provider == provider, Ticket.external_ticket_id == external_ticket_id
        )
        return await self._session.scalar(stmt)
