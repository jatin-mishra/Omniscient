from typing import Self
from uuid import UUID

from pydantic import EmailStr, field_validator

from app.onboarding.models import Status, User
from app.onboarding.schemas.common import EntityResponse, Name, StrictModel, reject_null


class UserCreate(StrictModel):
    name: Name
    email: EmailStr
    team_id: UUID


class UserUpdate(StrictModel):
    """No `email`: it is the identity key for IdP mapping, so it is immutable."""

    name: Name | None = None
    team_id: UUID | None = None
    status: Status | None = None

    _not_null = field_validator("name", "team_id", "status")(reject_null)


class UserResponse(EntityResponse):
    name: str
    email: str
    team_id: UUID

    @classmethod
    def from_model(cls, user: User, team_id: UUID) -> Self:
        return cls(
            id=user.external_id,
            name=user.name,
            email=user.email,
            team_id=team_id,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
