"""Ticket model rules (ids refer to metric/test_cases_and_metrics.yml, tracker section)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.tracker.models import (
    DocumentType,
    ProviderName,
    Ticket,
    TicketPriority,
    TicketStatus,
    TicketType,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
ACTOR = uuid4()


def make() -> Ticket:
    return Ticket(
        document_type=DocumentType.RCA,
        document_id=uuid4(),
        provider=ProviderName.INTERNAL,
        external_ticket_id="TKT-1",
        type=TicketType.TASK,
        title="t",
        priority=TicketPriority.LOW,
        status=TicketStatus.OPEN,
        reporter_id=uuid4(),
        created_by=ACTOR,
        updated_by=ACTOR,
    )


def test_resolve_sets_resolved_at_and_reopen_clears_it() -> None:  # M3, W2
    t = make()
    sys_actor = uuid4()
    assert t.apply_status_event(TicketStatus.RESOLVED, T0, sys_actor)
    assert (t.status, t.resolved_at, t.updated_by) == (TicketStatus.RESOLVED, T0, sys_actor)
    t.apply_status_event(TicketStatus.CLOSED, T0 + timedelta(hours=1), sys_actor)
    assert t.resolved_at == T0  # still the first resolution time
    t.apply_status_event(TicketStatus.IN_PROGRESS, T0 + timedelta(hours=2), sys_actor)
    assert t.resolved_at is None


def test_same_status_is_noop_but_moves_event_clock() -> None:  # M3, W3
    t = make()
    t.apply_status_event(TicketStatus.IN_PROGRESS, T0, uuid4())
    other = uuid4()
    t.apply_status_event(TicketStatus.IN_PROGRESS, T0 + timedelta(hours=1), other)
    assert t.updated_by != other
    assert t.last_event_at == T0 + timedelta(hours=1)


def test_stale_event_is_ignored_equal_is_applied() -> None:  # W4
    t = make()
    t.apply_status_event(TicketStatus.RESOLVED, T0, ACTOR)
    assert not t.apply_status_event(TicketStatus.OPEN, T0 - timedelta(seconds=1), ACTOR)
    assert t.status == TicketStatus.RESOLVED
    assert t.apply_status_event(TicketStatus.OPEN, T0, ACTOR)
    assert str(t.status) == "open"
