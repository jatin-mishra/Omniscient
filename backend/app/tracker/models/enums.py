from enum import StrEnum


class DocumentType(StrEnum):
    RCA = "rca"


class ProviderName(StrEnum):
    INTERNAL = "internal"


class TicketType(StrEnum):
    TASK = "task"
    BUG = "bug"
    ACTION_ITEM = "action_item"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


RESOLVED_STATUSES = frozenset({TicketStatus.RESOLVED, TicketStatus.CLOSED})
