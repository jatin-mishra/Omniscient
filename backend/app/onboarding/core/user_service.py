from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError
from app.onboarding.core.common import commit_or_conflict, require, require_active
from app.onboarding.models import Status, Team, User
from app.onboarding.repositories.team_repository import TeamRepository
from app.onboarding.repositories.user_repository import UserRepository
from app.onboarding.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession, users: UserRepository, teams: TeamRepository) -> None:
        self._session = session
        self._users = users
        self._teams = teams

    async def create(self, data: UserCreate) -> UserResponse:
        team = await self._active_team(data.team_id)
        email = data.email.lower()
        user = User(name=data.name, email=email, team_id=team.id)
        self._users.add(user)
        await commit_or_conflict(self._session, f"User with email '{email}' already exists")
        return UserResponse.from_model(user, team.external_id)

    async def get(self, user_id: UUID) -> UserResponse:
        user = require(await self._users.get_by_external_id(user_id), "User", user_id)
        team = await self._teams.get(user.team_id)
        return UserResponse.from_model(user, team.external_id)

    async def update(self, user_id: UUID, data: UserUpdate) -> UserResponse:
        user = require(await self._users.get_by_external_id(user_id), "User", user_id)
        team = await self._teams.get(user.team_id)

        if data.team_id is not None:
            team = await self._active_team(data.team_id)
            user.team_id = team.id
        if data.status is Status.INACTIVE and user.status is Status.ACTIVE:
            if await self._teams.find_active_managed_by(user.id):
                raise ConflictError("User manages an active team; reassign the manager first")
        if data.status is Status.ACTIVE and team.status is not Status.ACTIVE:
            raise ConflictError("User's team is inactive; move them to an active team")
        if data.status is not None:
            user.status = data.status
        if data.name is not None:
            user.name = data.name

        await self._session.commit()
        return UserResponse.from_model(user, team.external_id)

    async def _active_team(self, team_id: UUID) -> Team:
        team = require(await self._teams.get_by_external_id(team_id), "Team", team_id)
        require_active(team, "Team")
        return team
