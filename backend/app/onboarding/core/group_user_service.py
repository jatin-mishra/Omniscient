from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding.core.common import commit_or_conflict, require, require_active
from app.onboarding.models import GroupUser, Status
from app.onboarding.repositories.group_repository import GroupRepository
from app.onboarding.repositories.group_user_repository import GroupUserRepository
from app.onboarding.repositories.user_repository import UserRepository
from app.onboarding.schemas.group_user import GroupUserCreate, GroupUserResponse, GroupUserUpdate


class GroupUserService:
    def __init__(
        self,
        session: AsyncSession,
        memberships: GroupUserRepository,
        groups: GroupRepository,
        users: UserRepository,
    ) -> None:
        self._session = session
        self._memberships = memberships
        self._groups = groups
        self._users = users

    async def create(self, data: GroupUserCreate) -> GroupUserResponse:
        group = require(
            await self._groups.get_by_external_id(data.group_id), "Group", data.group_id
        )
        user = require(await self._users.get_by_external_id(data.user_id), "User", data.user_id)
        require_active(group, "Group")
        require_active(user, "User")
        membership = GroupUser(group_id=group.id, user_id=user.id)
        self._memberships.add(membership)
        await commit_or_conflict(self._session, "User is already a member of this group")
        return GroupUserResponse.from_model(membership, group.external_id, user.external_id)

    async def get(self, membership_id: UUID) -> GroupUserResponse:
        membership = await self._get(membership_id)
        group = await self._groups.get(membership.group_id)
        user = await self._users.get(membership.user_id)
        return GroupUserResponse.from_model(membership, group.external_id, user.external_id)

    async def update(self, membership_id: UUID, data: GroupUserUpdate) -> GroupUserResponse:
        membership = await self._get(membership_id)
        group = await self._groups.get(membership.group_id)
        user = await self._users.get(membership.user_id)
        if data.status is Status.ACTIVE:
            require_active(group, "Group")
            require_active(user, "User")
        if data.status is not None:
            membership.status = data.status
        await self._session.commit()
        return GroupUserResponse.from_model(membership, group.external_id, user.external_id)

    async def _get(self, membership_id: UUID) -> GroupUser:
        membership = await self._memberships.get_by_external_id(membership_id)
        return require(membership, "Group membership", membership_id)
