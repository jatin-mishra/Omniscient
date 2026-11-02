import logging
from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.helpers import commit_or_conflict
from app.errors import AppError, NotFoundError
from app.tracker.core.entity_verifier import EntityVerifier
from app.tracker.core.providers import (
    ExternalTicket,
    ProviderError,
    ProviderRegistry,
    TicketSpec,
)
from app.tracker.models import DocumentType, ProviderName, Ticket
from app.tracker.repositories.ticket_repository import TicketRepository
from app.tracker.schemas.ticket import TicketCreate, TicketResponse

log = logging.getLogger(__name__)

# Webhook updates have no user behind them
SYSTEM_ACTOR = UUID(int=0)


class TicketService:
    def __init__(
        self,
        session: AsyncSession,
        tickets: TicketRepository,
        providers: ProviderRegistry,
        verifier: EntityVerifier,
    ) -> None:
        self._session = session
        self._tickets = tickets
        self._providers = providers
        self._verifier = verifier

    async def create(self, data: TicketCreate, actor: UUID) -> TicketResponse:
        for user_id in (data.reporter_id, data.assignee_id):
            if user_id is not None:
                await self._require_user(user_id)
        reporter_id = data.reporter_id or actor

        provider = self._providers.get(data.provider.value)
        spec = TicketSpec(
            document_type=data.document_type,
            document_id=data.document_id,
            type=data.type,
            title=data.title,
            description=data.description,
            priority=data.priority,
            assignee_id=data.assignee_id,
            reporter_id=reporter_id,
            due_at=data.due_at,
        )
        try:
            external = await provider.create_ticket(spec)
        except AppError:
            raise
        except Exception as exc:
            log.exception("ticket provider %s failed", provider.name)
            raise ProviderError(f"Ticket provider '{provider.name}' failed") from exc

        ticket = self._build(spec, provider.name, external, actor)
        self._tickets.add(ticket)
        await commit_or_conflict(self._session, "This provider ticket already exists")
        return TicketResponse.from_model(ticket)

    async def list_for_document(
        self, document_type: DocumentType, document_id: UUID
    ) -> Sequence[TicketResponse]:
        tickets = await self._tickets.list_for_document(document_type, document_id)
        return [TicketResponse.from_model(t) for t in tickets]

    async def handle_status_webhook(
        self, provider_name: str, headers: Mapping[str, str], body: bytes
    ) -> None:
        provider = self._providers.get(provider_name)
        event = provider.parse_status_event(headers, body)
        ticket = await self._tickets.find_by_provider_ticket(
            provider.name, event.external_ticket_id
        )
        if ticket is None:
            raise NotFoundError(f"Ticket {event.external_ticket_id} not found")
        if ticket.apply_status_event(event.status, event.occurred_at, SYSTEM_ACTOR):
            await self._session.commit()
        else:
            log.info("ignored stale event for ticket %s", event.external_ticket_id)

    @staticmethod
    def _build(
        spec: TicketSpec, provider: ProviderName, external: ExternalTicket, actor: UUID
    ) -> Ticket:
        return Ticket(
            document_type=spec.document_type,
            document_id=spec.document_id,
            provider=provider,
            external_ticket_id=external.external_ticket_id,
            type=spec.type,
            title=spec.title,
            description=spec.description,
            priority=spec.priority,
            status=external.status,
            assignee_id=spec.assignee_id,
            reporter_id=spec.reporter_id,
            due_at=spec.due_at,
            created_by=actor,
            updated_by=actor,
        )

    async def _require_user(self, user_id: UUID) -> None:
        # False = owner says it is missing. None = nobody can answer, accept unverified.
        if await self._verifier.exists("user", user_id) is False:
            raise NotFoundError(f"user {user_id} not found")
