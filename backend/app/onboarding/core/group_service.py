from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding.core.common import commit_or_conflict, require
from app.onboarding.models import Group
from app.onboarding.repositories.group_repository import GroupRepository
from app.onboarding.schemas.group import GroupCreate, GroupResponse, GroupUpdate


class GroupService:
    def __init__(self, session: AsyncSession, groups: GroupRepository) -> None:
        self._session = session
        self._groups = groups

    async def create(self, data: GroupCreate) -> GroupResponse:
        group = Group(name=data.name)
        self._groups.add(group)
        await commit_or_conflict(self._session, f"Group '{data.name}' already exists")
        return GroupResponse.from_model(group)

    async def get(self, group_id: UUID) -> GroupResponse:
        group = require(await self._groups.get_by_external_id(group_id), "Group", group_id)
        return GroupResponse.from_model(group)

    async def update(self, group_id: UUID, data: GroupUpdate) -> GroupResponse:
        group = require(await self._groups.get_by_external_id(group_id), "Group", group_id)
        if data.status is not None:
            group.status = data.status
        if data.name is not None:
            group.name = data.name
        await commit_or_conflict(self._session, f"Group '{data.name}' already exists")
        return GroupResponse.from_model(group)
