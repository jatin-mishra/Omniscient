"""tracker against real Postgres (ids refer to metric/test_cases_and_metrics.yml)."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db.postgres import create_db
from app.main import app
from app.tracker.models import (
    DocumentType,
    ProviderName,
    Ticket,
    TicketPriority,
    TicketType,
)
from tests.tracker.fakes import SECRET, event_body, sign

pytestmark = pytest.mark.integration

H = {"X-User-Id": str(uuid4())}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CREATE_SCHEMA_ON_STARTUP", "true")  # I1: schema made at startup
    monkeypatch.setenv("TRACKER_WEBHOOK_SECRET", SECRET)
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_create_list_webhook_flow(api: TestClient) -> None:  # I2
    doc = str(uuid4())
    body = {
        "document_type": "rca",
        "document_id": doc,
        "type": "action_item",
        "title": "Add alert",
        "priority": "critical",
        "due_at": "2026-12-01T00:00:00Z",
    }
    created = api.post("/v1/tickets", json=body, headers=H)
    assert created.status_code == 201, created.text
    ticket = created.json()

    payload = event_body(ticket["external_ticket_id"], "resolved")
    res = api.post(
        "/v1/tickets/webhooks/internal", content=payload, headers={"X-Signature": sign(payload)}
    )
    assert res.status_code == 204, res.text

    listed = api.get(f"/v1/tickets?document_type=rca&document_id={doc}", headers=H).json()
    assert [t["id"] for t in listed] == [ticket["id"]]
    assert listed[0]["status"] == "resolved" and listed[0]["resolved_at"] is not None


def test_provider_ticket_is_unique_in_postgres() -> None:  # I3, M2
    async def run() -> None:
        engine, sessionmaker = create_db(get_settings())
        doc, ext = uuid4(), f"TKT-{uuid4().hex[:8]}"

        def row() -> Ticket:
            return Ticket(
                document_type=DocumentType.RCA,
                document_id=doc,
                provider=ProviderName.INTERNAL,
                external_ticket_id=ext,
                type=TicketType.TASK,
                title="t",
                priority=TicketPriority.LOW,
                reporter_id=uuid4(),
                created_by=uuid4(),
                updated_by=uuid4(),
                due_at=datetime.now(UTC),
            )

        async with sessionmaker() as session:
            session.add(row())
            await session.commit()
        async with sessionmaker() as session:
            session.add(row())
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(run())
