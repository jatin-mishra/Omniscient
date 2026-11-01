from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.onboarding.models import Status

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class StrictModel(BaseModel):
    """Request base: unknown fields are a 422, so a typo is never silently ignored."""

    model_config = ConfigDict(extra="forbid")


def reject_null[T](value: T | None) -> T:
    """For PATCH fields that may be omitted but not set to null. Runs only when the field is
    sent (defaults are not validated), so omission still means 'leave unchanged'."""
    if value is None:
        raise ValueError("may be omitted but not null")
    return value


class EntityResponse(BaseModel):
    id: UUID
    status: Status
    created_at: datetime
    updated_at: datetime
