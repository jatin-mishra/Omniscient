import hashlib
import hmac
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.tracker.core.providers import InternalProvider, ProviderRegistry, TicketSpec
from app.tracker.core.providers.base import ExternalTicket
from app.tracker.core.ticket_service import TicketService
from app.tracker.models import DocumentType, ProviderName, Ticket
from tests.onboarding.fakes import FakeRepo, FakeSession

SECRET = "s3cret"


def sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def event_body(ticket_id: str, status: str, occurred_at: datetime | None = None) -> bytes:
    at = (occurred_at or datetime.now(UTC)).isoformat()
    return json.dumps(
        {"external_ticket_id": ticket_id, "status": status, "occurred_at": at}
    ).encode()


class FakeTickets(FakeRepo[Ticket]):
    async def list_for_document(
        self, document_type: DocumentType, document_id: UUID
    ) -> Sequence[Ticket]:
        rows = [
            t
            for t in self.rows
            if t.document_type == document_type and t.document_id == document_id
        ]
        return sorted(rows, key=lambda t: t.id, reverse=True)

    async def find_by_provider_ticket(
        self, provider: ProviderName, external_ticket_id: str
    ) -> Ticket | None:
        return next(
            (
                t
                for t in self.rows
                if t.provider == provider and t.external_ticket_id == external_ticket_id
            ),
            None,
        )


class FakeVerifier:
    def __init__(self) -> None:
        self.known: set[UUID] = set()
        self.unverifiable = False
        self.calls: list[tuple[str, UUID]] = []

    def add(self) -> UUID:
        id_ = uuid4()
        self.known.add(id_)
        return id_

    async def exists(self, kind: str, external_id: UUID) -> bool | None:
        self.calls.append((kind, external_id))
        return None if self.unverifiable else external_id in self.known


class RaisingProvider(InternalProvider):
    async def create_ticket(self, spec: TicketSpec) -> ExternalTicket:
        raise RuntimeError("boom")


class FakeSessionCounting(FakeSession):
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeDb:
    def __init__(self, provider: InternalProvider | None = None) -> None:
        self.session = FakeSessionCounting()
        self.repo = FakeTickets()
        self.verifier = FakeVerifier()
        self.service = TicketService(
            self.session,  # type: ignore[arg-type]
            self.repo,  # type: ignore[arg-type]
            ProviderRegistry([provider or InternalProvider(SECRET)]),
            self.verifier,
        )
