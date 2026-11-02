from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.constants.permissions import ALL, ResourceType
from app.constants.status import Status
from app.policy_engine.models import EntityType, UserPermission
from app.policy_engine.schemas.common import StrictModel


class UserPermissionCreate(StrictModel):
    entity_type: EntityType
    entity_id: UUID
    policy_id: UUID
    resource_type: ResourceType
    resource_id: UUID | Literal["ALL"]

    @model_validator(mode="after")
    def _resource_shape(self) -> Self:
        is_all = self.resource_id == ALL
        if is_all != (self.resource_type is ResourceType.ALL):
            raise ValueError('resource_id "ALL" and resource_type ALL must be used together')
        return self


class UserPermissionUpdate(StrictModel):
    status: Status  # the only updatable field, so it is required


class UserPermissionResponse(BaseModel):
    id: UUID
    entity_type: EntityType
    entity_id: UUID
    policy_id: UUID
    resource_type: ResourceType
    resource_id: str
    status: Status
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_model(cls, grant: UserPermission, policy_id: UUID) -> Self:
        return cls(
            id=grant.external_id,
            entity_type=grant.entity_type,
            entity_id=grant.entity_id,
            policy_id=policy_id,
            resource_type=grant.resource_type,
            resource_id=grant.resource_id,
            status=grant.status,
            created_at=grant.created_at,
            created_by=grant.created_by,
            updated_at=grant.updated_at,
            updated_by=grant.updated_by,
        )
