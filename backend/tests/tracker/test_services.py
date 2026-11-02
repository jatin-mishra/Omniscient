"""Business rules (ids refer to metric/test_cases_and_metrics.yml, tracker section)."""

import hmac
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from app.errors import ConflictError, InvalidRequestError, NotFoundError, UnauthorizedError
from app.tracker.core.providers import InternalProvider, ProviderError, ProviderRegistry
from app.tracker.models import DocumentType, TicketStatus
from app.tracker.schemas.ticket import TicketCreate
from tests.tracker.fakes import SECRET, FakeDb, RaisingProvider, event_body, sign

ACTOR = uuid4()
DOC = uuid4()
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


def body(**over: Any) -> TicketCreate:
    fields: dict[str, Any] = {
        "document_type": "rca",
        "document_id": DOC,
        "type": "task",
        "title": "Fix it",
        "priority": "high",
    }
    return TicketCreate(**{**fields, **over})


async def hook(db: FakeDb, payload: bytes, sig: str | None = None, name: str = "internal") -> None:
    headers = {"x-signature": sig if sig is not None else sign(payload)}
    await db.service.handle_status_webhook(name, headers, payload)


async def test_create_defaults_and_actor(db: FakeDb) -> None:  # T1, T2, T8
    res = await db.service.create(body(), ACTOR)
    assert res.status is TicketStatus.OPEN
    assert res.external_ticket_id.startswith("TKT-")  # P2
    assert (res.reporter_id, res.assignee_id) == (ACTOR, None)
    assert (res.created_by, res.updated_by) == (ACTOR, ACTOR)
    assert db.session.commits == 1


async def test_external_ids_are_unique(db: FakeDb) -> None:  # P2
    a = await db.service.create(body(), ACTOR)
    b = await db.service.create(body(), ACTOR)
    assert a.external_ticket_id != b.external_ticket_id


async def test_missing_user_is_404_unverifiable_is_accepted(db: FakeDb) -> None:  # T6
    with pytest.raises(NotFoundError):
        await db.service.create(body(assignee_id=uuid4()), ACTOR)
    with pytest.raises(NotFoundError):
        await db.service.create(body(reporter_id=uuid4()), ACTOR)
    known = db.verifier.add()
    await db.service.create(body(assignee_id=known, reporter_id=known), ACTOR)
    db.verifier.unverifiable = True
    await db.service.create(body(assignee_id=uuid4()), ACTOR)
    assert db.session.commits == 2


async def test_default_reporter_is_not_verified(db: FakeDb) -> None:  # T2
    await db.service.create(body(), ACTOR)
    assert db.verifier.calls == []


async def test_provider_failure_is_502_and_nothing_persisted(db: FakeDb) -> None:  # P5
    failing = FakeDb(RaisingProvider(SECRET))
    with pytest.raises(ProviderError) as err:
        await failing.service.create(body(), ACTOR)
    assert err.value.status_code == 502
    assert failing.repo.rows == [] and failing.session.commits == 0


async def test_commit_conflict_is_409(db: FakeDb) -> None:  # T9
    async def boom() -> None:
        from sqlalchemy.exc import IntegrityError

        raise IntegrityError("x", {}, Exception())

    db.session.commit = boom  # type: ignore[method-assign]
    with pytest.raises(ConflictError):
        await db.service.create(body(), ACTOR)


async def test_list_filters_by_document_newest_first(db: FakeDb) -> None:  # G1-G3
    assert await db.service.list_for_document(DocumentType.RCA, DOC) == []
    first = await db.service.create(body(title="a"), ACTOR)
    second = await db.service.create(body(title="b"), ACTOR)
    await db.service.create(body(document_id=uuid4()), ACTOR)
    got = await db.service.list_for_document(DocumentType.RCA, DOC)
    assert [t.id for t in got] == [second.id, first.id]


async def test_webhook_updates_status_with_system_actor(db: FakeDb) -> None:  # W1, W2
    t = await db.service.create(body(), ACTOR)
    await hook(db, event_body(t.external_ticket_id, "resolved"))
    row = db.repo.rows[0]
    assert row.status is TicketStatus.RESOLVED and row.resolved_at is not None
    assert row.updated_by.int == 0
    await hook(db, event_body(t.external_ticket_id, "open", datetime.now(UTC) + timedelta(1)))
    assert row.resolved_at is None


async def test_webhook_is_idempotent(db: FakeDb) -> None:  # W3
    t = await db.service.create(body(), ACTOR)
    payload = event_body(t.external_ticket_id, "in_progress")
    await hook(db, payload)
    await hook(db, payload)
    assert db.repo.rows[0].status is TicketStatus.IN_PROGRESS


async def test_stale_webhook_does_not_commit(db: FakeDb) -> None:  # W4
    t = await db.service.create(body(), ACTOR)
    now = datetime.now(UTC)
    await hook(db, event_body(t.external_ticket_id, "resolved", now))
    commits = db.session.commits
    await hook(db, event_body(t.external_ticket_id, "open", now - timedelta(minutes=5)))
    assert db.repo.rows[0].status is TicketStatus.RESOLVED
    assert db.session.commits == commits


@pytest.mark.parametrize("sig", ["", "deadbeef", None])  # W5
async def test_bad_signature_is_401_and_ticket_untouched(db: FakeDb, sig: str | None) -> None:
    t = await db.service.create(body(), ACTOR)
    payload = event_body(t.external_ticket_id, "closed")
    headers = {} if sig is None else {"x-signature": sig}
    with pytest.raises(UnauthorizedError):
        await db.service.handle_status_webhook("internal", headers, payload)
    assert db.repo.rows[0].status is TicketStatus.OPEN


async def test_signature_covers_exact_body(db: FakeDb) -> None:  # W6
    t = await db.service.create(body(), ACTOR)
    good = event_body(t.external_ticket_id, "open")
    with pytest.raises(UnauthorizedError):
        await hook(db, good + b" ", sig=sign(good))


async def test_empty_secret_rejects_everything() -> None:  # C2
    db = FakeDb(InternalProvider(""))
    payload = event_body("TKT-1", "open")
    with pytest.raises(UnauthorizedError):
        await db.service.handle_status_webhook(
            "internal", {"x-signature": sign(payload, "")}, payload
        )


def test_signature_compare_is_constant_time() -> None:  # W7
    import inspect

    from app.tracker.core.providers import internal

    assert "compare_digest" in inspect.getsource(internal)
    assert hmac.compare_digest("a", "a")


async def test_unknown_provider_and_ticket_are_404(db: FakeDb) -> None:  # W8, W9
    payload = event_body("TKT-nope", "open")
    with pytest.raises(NotFoundError):
        await hook(db, payload, name="jira")
    with pytest.raises(NotFoundError):
        await hook(db, payload)


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b'{"external_ticket_id": "x"}',
        b'{"external_ticket_id": "x", "status": "weird", "occurred_at": "2026-01-01T00:00:00Z"}',
        b'{"external_ticket_id": "x", "status": "open", "occurred_at": "2026-01-01T00:00:00"}',
    ],
)  # W10, W13, P4
async def test_malformed_payload_is_422(db: FakeDb, payload: bytes) -> None:
    with pytest.raises(InvalidRequestError):
        await hook(db, payload)


async def test_other_providers_ticket_not_matched(db: FakeDb) -> None:  # W12
    t = await db.service.create(body(), ACTOR)
    db.repo.rows[0].provider = "jira"  # type: ignore[assignment]
    with pytest.raises(NotFoundError):
        await hook(db, event_body(t.external_ticket_id, "open"))


def test_registry_unknown_name_is_404() -> None:  # P3
    with pytest.raises(NotFoundError):
        ProviderRegistry([InternalProvider(SECRET)]).get("jira")
