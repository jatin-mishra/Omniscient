from sqlalchemy import select

from app.onboarding.models import Status, Team
from app.onboarding.repositories.base import Repository


class TeamRepository(Repository[Team]):
    model = Team

    async def find_active_managed_by(self, user_id: int) -> Team | None:
        stmt = select(Team).where(Team.manager_id == user_id, Team.status == Status.ACTIVE).limit(1)
        return await self._session.scalar(stmt)
