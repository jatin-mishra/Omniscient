from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError
from app.onboarding.core.common import commit_or_conflict, require, require_active
from app.onboarding.models import Status, Team, User
from app.onboarding.repositories.team_repository import TeamRepository
from app.onboarding.repositories.user_repository import UserRepository
from app.onboarding.schemas.team import TeamCreate, TeamResponse, TeamUpdate


class TeamService:
    def __init__(self, session: AsyncSession, teams: TeamRepository, users: UserRepository) -> None:
        self._session = session
        self._teams = teams
        self._users = users

    async def create(self, data: TeamCreate) -> TeamResponse:
        manager = await self._active_manager(data.manager_id)
        team = Team(name=data.name, manager_id=manager.id if manager else None)
        self._teams.add(team)
        await commit_or_conflict(self._session, f"Team '{data.name}' already exists")
        return TeamResponse.from_model(team, data.manager_id)

    async def get(self, team_id: UUID) -> TeamResponse:
        team = require(await self._teams.get_by_external_id(team_id), "Team", team_id)
        manager = await self._users.get(team.manager_id) if team.manager_id else None
        return TeamResponse.from_model(team, manager.external_id if manager else None)

    async def update(self, team_id: UUID, data: TeamUpdate) -> TeamResponse:
        team = require(await self._teams.get_by_external_id(team_id), "Team", team_id)
        manager = await self._users.get(team.manager_id) if team.manager_id else None

        if "manager_id" in data.model_fields_set:  # null is meaningful here: clear the manager
            manager = await self._active_manager(data.manager_id)
            team.manager_id = manager.id if manager else None
        if data.status is Status.INACTIVE and team.status is Status.ACTIVE:
            if await self._users.find_active_in_team(team.id):
                raise ConflictError("Team has active users; move or deactivate them first")
        if data.status is Status.ACTIVE and manager and manager.status is not Status.ACTIVE:
            raise ConflictError("Team manager is inactive; set an active manager or clear it")
        if data.status is not None:
            team.status = data.status
        if data.name is not None:
            team.name = data.name

        await commit_or_conflict(self._session, f"Team '{data.name}' already exists")
        return TeamResponse.from_model(team, manager.external_id if manager else None)

    async def _active_manager(self, user_id: UUID | None) -> User | None:
        if user_id is None:
            return None
        user = require(await self._users.get_by_external_id(user_id), "User", user_id)
        require_active(user, "User")
        return user
