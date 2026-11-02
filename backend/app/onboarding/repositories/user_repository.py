from sqlalchemy import select

from app.onboarding.models import Status, User
from app.onboarding.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    async def find_active_in_team(self, team_id: int) -> User | None:
        stmt = select(User).where(User.team_id == team_id, User.status == Status.ACTIVE).limit(1)
        return await self._session.scalar(stmt)
