from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.status import Status
from app.db.helpers import commit_or_conflict, require
from app.errors import ConflictError
from app.policy_engine.models import Policy
from app.policy_engine.repositories.policy_repository import PolicyRepository
from app.policy_engine.repositories.user_permission_repository import UserPermissionRepository
from app.policy_engine.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate


class PolicyService:
    def __init__(
        self,
        session: AsyncSession,
        policies: PolicyRepository,
        user_permissions: UserPermissionRepository,
    ) -> None:
        self._session = session
        self._policies = policies
        self._user_permissions = user_permissions

    async def create(self, data: PolicyCreate, actor: UUID) -> PolicyResponse:
        policy = Policy(
            permission_name=data.permission_name.value,
            effect=data.effect,
            created_by=actor,
            updated_by=actor,
        )
        self._policies.add(policy)
        await commit_or_conflict(
            self._session,
            f"A {data.effect} policy for '{data.permission_name}' already exists",
        )
        return PolicyResponse.from_model(policy)

    async def update(self, policy_id: UUID, data: PolicyUpdate, actor: UUID) -> PolicyResponse:
        policy = require(await self._policies.get_by_external_id(policy_id), "Policy", policy_id)
        if data.status is Status.INACTIVE and policy.status is Status.ACTIVE:
            if await self._user_permissions.find_active_for_policy(policy.id):
                raise ConflictError("Policy has active user permissions; deactivate them first")
        policy.set_status(data.status, actor)
        await self._session.commit()
        return PolicyResponse.from_model(policy)
