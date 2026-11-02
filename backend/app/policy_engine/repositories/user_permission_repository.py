from sqlalchemy import select

from app.constants.status import Status
from app.db.repository import Repository
from app.policy_engine.models import UserPermission


class UserPermissionRepository(Repository[UserPermission]):
    model = UserPermission

    async def find_active_for_policy(self, policy_id: int) -> UserPermission | None:
        stmt = (
            select(UserPermission)
            .where(UserPermission.policy_id == policy_id, UserPermission.status == Status.ACTIVE)
            .limit(1)
        )
        return await self._session.scalar(stmt)
