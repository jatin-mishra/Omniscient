from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from app.constants.permissions import PermissionName
from app.constants.status import Status
from app.policy_engine.models import Effect, Policy
from app.policy_engine.schemas.common import StrictModel


class PolicyCreate(StrictModel):
    permission_name: PermissionName
    effect: Effect


class PolicyUpdate(StrictModel):
    status: Status  # the only updatable field, so it is required


class PolicyResponse(BaseModel):
    id: UUID
    permission_name: PermissionName
    effect: Effect
    status: Status
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_model(cls, policy: Policy) -> Self:
        return cls(
            id=policy.external_id,
            permission_name=PermissionName(policy.permission_name),
            effect=policy.effect,
            status=policy.status,
            created_at=policy.created_at,
            created_by=policy.created_by,
            updated_at=policy.updated_at,
            updated_by=policy.updated_by,
        )
