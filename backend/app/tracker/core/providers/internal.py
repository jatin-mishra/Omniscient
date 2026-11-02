import hashlib
import hmac
from collections.abc import Mapping
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ValidationError

from app.errors import InvalidRequestError, UnauthorizedError
from app.tracker.core.providers.base import ExternalTicket, StatusEvent, TicketSpec
from app.tracker.models import ProviderName, TicketStatus

SIGNATURE_HEADER = "x-signature"


class _InternalEvent(BaseModel):
    external_ticket_id: str
    status: TicketStatus
    occurred_at: AwareDatetime


class InternalProvider:
    """Tickets owned by this system. The webhook body is signed with HMAC-SHA256 of the raw
    bytes (hex, in `X-Signature`) using a shared secret."""

    name = ProviderName.INTERNAL

    def __init__(self, webhook_secret: str) -> None:
        self._secret = webhook_secret.encode()

    async def create_ticket(self, spec: TicketSpec) -> ExternalTicket:
        return ExternalTicket(f"TKT-{uuid4().hex[:8]}", TicketStatus.OPEN)

    def parse_status_event(self, headers: Mapping[str, str], body: bytes) -> StatusEvent:
        self._verify(headers.get(SIGNATURE_HEADER), body)
        try:
            event = _InternalEvent.model_validate_json(body)
        except ValidationError as exc:
            raise InvalidRequestError("Malformed webhook payload") from exc
        return StatusEvent(event.external_ticket_id, event.status, event.occurred_at)

    def _verify(self, signature: str | None, body: bytes) -> None:
        # Fail closed: with no secret configured nothing can be authenticated
        if not self._secret or not signature:
            raise UnauthorizedError("Invalid webhook signature")
        expected = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise UnauthorizedError("Invalid webhook signature")
