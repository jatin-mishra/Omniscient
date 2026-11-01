from typing import Self

from pydantic import field_validator

from app.onboarding.models import Group, Status
from app.onboarding.schemas.common import EntityResponse, Name, StrictModel, reject_null


class GroupCreate(StrictModel):
    name: Name


class GroupUpdate(StrictModel):
    name: Name | None = None
    status: Status | None = None

    _not_null = field_validator("name", "status")(reject_null)


class GroupResponse(EntityResponse):
    name: str

    @classmethod
    def from_model(cls, group: Group) -> Self:
        return cls(
            id=group.external_id,
            name=group.name,
            status=group.status,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
