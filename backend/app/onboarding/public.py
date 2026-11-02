"""The narrow surface other modules (via the root layer) may call. Keeps onboarding's tables
private: callers ask a question, they never query onboarding's models."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import Repository
from app.onboarding.repositories.group_repository import GroupRepository
from app.onboarding.repositories.team_repository import TeamRepository
from app.onboarding.repositories.user_repository import UserRepository

_REPOSITORIES: dict[str, type[Repository[Any]]] = {
    "team": TeamRepository,
    "group": GroupRepository,
    "user": UserRepository,
}

KINDS = frozenset(_REPOSITORIES)


async def entity_exists(session: AsyncSession, kind: str, external_id: UUID) -> bool:
    return await _REPOSITORIES[kind](session).get_by_external_id(external_id) is not None
