from typing import Self
from uuid import UUID

from pydantic import field_validator

from app.onboarding.models import GroupUser, Status
from app.onboarding.schemas.common import EntityResponse, StrictModel, reject_null


class GroupUserCreate(StrictModel):
    group_id: UUID
    user_id: UUID


class GroupUserUpdate(StrictModel):
    status: Status | None = None

    _not_null = field_validator("status")(reject_null)


class GroupUserResponse(EntityResponse):
    group_id: UUID
    user_id: UUID

    @classmethod
    def from_model(cls, membership: GroupUser, group_id: UUID, user_id: UUID) -> Self:
        return cls(
            id=membership.external_id,
            group_id=group_id,
            user_id=user_id,
            status=membership.status,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )
