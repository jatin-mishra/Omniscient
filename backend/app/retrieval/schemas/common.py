from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.constants.status import Status


def _constrained(max_length: int) -> StringConstraints:
    return StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)


Name = Annotated[str, _constrained(128)]
DocumentName = Annotated[str, _constrained(255)]
Label32 = Annotated[str, _constrained(32)]
Label64 = Annotated[str, _constrained(64)]
Label128 = Annotated[str, _constrained(128)]
Bucket = Annotated[str, _constrained(255)]
StoragePath = Annotated[str, _constrained(1024)]
StorageUrl = Annotated[str, _constrained(2048)]


class StrictModel(BaseModel):
    """Request base: unknown fields are a 422, so a typo is never silently ignored."""

    model_config = ConfigDict(extra="forbid")


def reject_null[T](value: T | None) -> T:
    """For PATCH fields that may be omitted but not set to null. Runs only when the field is
    sent (defaults are not validated), so omission still means 'leave unchanged'."""
    if value is None:
        raise ValueError("may be omitted but not null")
    return value


class AuditedResponse(BaseModel):
    id: UUID
    status: Status
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
