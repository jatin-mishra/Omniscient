from typing import Self
from uuid import UUID

from pydantic import field_validator

from app.onboarding.models import Status, Team
from app.onboarding.schemas.common import EntityResponse, Name, StrictModel, reject_null


class TeamCreate(StrictModel):
    name: Name
    manager_id: UUID | None = None


class TeamUpdate(StrictModel):
    name: Name | None = None
    manager_id: UUID | None = None  # null clears the manager
    status: Status | None = None

    _not_null = field_validator("name", "status")(reject_null)


class TeamResponse(EntityResponse):
    name: str
    manager_id: UUID | None

    @classmethod
    def from_model(cls, team: Team, manager_id: UUID | None) -> Self:
        return cls(
            id=team.external_id,
            name=team.name,
            manager_id=manager_id,
            status=team.status,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
