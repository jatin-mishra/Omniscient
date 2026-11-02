"""HTTP layer only: validation, auth header, status codes (ids: tracker section of the spec)."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tracker.deps import get_ticket_service
from app.tracker.models import (
    DocumentType,
    ProviderName,
    TicketPriority,
    TicketStatus,
    TicketType,
)
from app.tracker.schemas.ticket import TicketResponse
from tests.tracker.fakes import FakeDb, event_body, sign

NOW = datetime.now(UTC)
H = {"X-User-Id": str(uuid4())}
DOC = str(uuid4())
VALID: dict[str, Any] = {
    "document_type": "rca",
    "document_id": DOC,
    "type": "task",
    "title": "Fix it",
    "priority": "high",
}
TICKET = TicketResponse(
    id=uuid4(),
    document_type=DocumentType.RCA,
    document_id=uuid4(),
    provider=ProviderName.INTERNAL,
    external_ticket_id="TKT-1",
    type=TicketType.TASK,
    title="Fix it",
    description=None,
    priority=TicketPriority.HIGH,
    status=TicketStatus.OPEN,
    assignee_id=None,
    reporter_id=uuid4(),
    created_at=NOW,
    created_by=uuid4(),
    updated_at=NOW,
    updated_by=uuid4(),
    resolved_at=None,
    due_at=None,
)


class StubService:
    async def create(self, *_: Any) -> TicketResponse:
        return TICKET

    async def list_for_document(self, *_: Any) -> Sequence[TicketResponse]:
        return [TICKET]


class NeverCalled:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"service.{name} called for an invalid request")


@pytest.fixture(autouse=True)
def stub_service() -> None:
    app.dependency_overrides[get_ticket_service] = NeverCalled


def use_stub() -> None:
    app.dependency_overrides[get_ticket_service] = StubService


def test_create_201_hides_internal_id(client: TestClient) -> None:  # T1
    use_stub()
    res = client.post("/v1/tickets", json=VALID, headers=H)
    assert res.status_code == 201
    assert res.json()["id"] == str(TICKET.id)
    assert "external_id" not in res.json() and "resolved_at" in res.json()


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "nope"}])  # T3, G5
def test_missing_or_bad_actor_is_401(client: TestClient, headers: dict[str, str]) -> None:
    assert client.post("/v1/tickets", json=VALID, headers=headers).status_code == 401
    url = f"/v1/tickets?document_type=rca&document_id={DOC}"
    assert client.get(url, headers=headers).status_code == 401


@pytest.mark.parametrize(
    "over",
    [
        {"title": "  "},
        {"title": "x" * 101},
        {"description": "x" * 2001},
        {"document_type": "wiki"},
        {"document_id": "nope"},
        {"priority": "urgent"},
        {"type": "epic"},
        {"provider": "jira"},
        {"due_at": "2026-01-01T00:00:00"},  # naive
        {"status": "closed"},  # T5
        {"resolved_at": "2026-01-01T00:00:00Z"},
        {"external_ticket_id": "X"},
        {"created_by": str(uuid4())},
        {"unknown": 1},
    ],
)  # T4, T5, T7, T10
def test_invalid_create_is_422(client: TestClient, over: dict[str, Any]) -> None:
    assert client.post("/v1/tickets", json={**VALID, **over}, headers=H).status_code == 422


def test_boundary_lengths_and_past_due_are_accepted(client: TestClient) -> None:  # T7, T10
    use_stub()
    body = {
        **VALID,
        "title": "x" * 100,
        "description": "y" * 2000,
        "due_at": "2000-01-01T00:00:00Z",
    }
    assert client.post("/v1/tickets", json=body, headers=H).status_code == 201


def test_list_200(client: TestClient) -> None:  # G1
    use_stub()
    res = client.get(f"/v1/tickets?document_type=rca&document_id={DOC}", headers=H)
    assert res.status_code == 200 and res.json()[0]["id"] == str(TICKET.id)


@pytest.mark.parametrize(
    "query",
    [
        "",
        f"?document_id={DOC}",
        "?document_type=rca",
        "?document_type=rca&document_id=x",
        f"?document_type=wiki&document_id={DOC}",
    ],
)  # G4
def test_invalid_list_query_is_422(client: TestClient, query: str) -> None:
    assert client.get(f"/v1/tickets{query}", headers=H).status_code == 422


@pytest.fixture
def real() -> FakeDb:
    db = FakeDb()
    app.dependency_overrides[get_ticket_service] = lambda: db.service
    return db


def test_webhook_end_to_end_without_user_header(
    client: TestClient, real: FakeDb
) -> None:  # W1, W11
    created = client.post("/v1/tickets", json=VALID, headers=H).json()
    payload = event_body(created["external_ticket_id"], "resolved")
    res = client.post(
        "/v1/tickets/webhooks/internal", content=payload, headers={"X-Signature": sign(payload)}
    )
    assert res.status_code == 204 and res.content == b""
    listed = client.get(f"/v1/tickets?document_type=rca&document_id={DOC}", headers=H).json()
    assert listed[0]["status"] == "resolved" and listed[0]["resolved_at"] is not None


def test_webhook_error_mapping(client: TestClient, real: FakeDb) -> None:  # W5, W8, W9, W10
    created = client.post("/v1/tickets", json=VALID, headers=H).json()
    payload = event_body(created["external_ticket_id"], "closed")
    url = "/v1/tickets/webhooks/internal"
    assert client.post(url, content=payload).status_code == 401
    assert client.post(url, content=payload, headers={"X-Signature": "bad"}).status_code == 401
    assert (
        client.post(
            url.replace("internal", "jira"), content=payload, headers={"X-Signature": sign(payload)}
        ).status_code
        == 404
    )
    unknown = event_body("TKT-none", "open")
    assert (
        client.post(url, content=unknown, headers={"X-Signature": sign(unknown)}).status_code == 404
    )
    junk = b"{}"
    assert client.post(url, content=junk, headers={"X-Signature": sign(junk)}).status_code == 422
    assert real.repo.rows[0].status is TicketStatus.OPEN


def test_provider_failure_maps_to_502(client: TestClient) -> None:  # P5
    from tests.tracker.fakes import RaisingProvider

    db = FakeDb(RaisingProvider("s"))
    app.dependency_overrides[get_ticket_service] = lambda: db.service
    res = client.post("/v1/tickets", json=VALID, headers=H)
    assert res.status_code == 502 and res.json()["error"]["code"] == "ticket_provider_error"
