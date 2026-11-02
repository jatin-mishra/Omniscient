from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.permissions import ALLOWED_RESOURCES, PermissionName, ResourceType
from app.constants.status import Status
from app.db.helpers import commit_or_conflict, require
from app.errors import ConflictError, InvalidRequestError, NotFoundError
from app.policy_engine.core.entity_verifier import EntityVerifier
from app.policy_engine.models import Policy, UserPermission
from app.policy_engine.repositories.policy_repository import PolicyRepository
from app.policy_engine.repositories.user_permission_repository import UserPermissionRepository
from app.policy_engine.schemas.user_permission import (
    UserPermissionCreate,
    UserPermissionResponse,
    UserPermissionUpdate,
)


def check_resource_allowed(permission: PermissionName, resource_type: ResourceType) -> None:
    """Static rule: which resource types a permission can be scoped to. "ALL" always passes."""
    if resource_type is not ResourceType.ALL and resource_type not in ALLOWED_RESOURCES[permission]:
        raise InvalidRequestError(f"'{permission}' cannot be scoped to a {resource_type}")


class UserPermissionService:
    def __init__(
        self,
        session: AsyncSession,
        policies: PolicyRepository,
        user_permissions: UserPermissionRepository,
        verifier: EntityVerifier,
    ) -> None:
        self._session = session
        self._policies = policies
        self._user_permissions = user_permissions
        self._verifier = verifier

    async def create(self, data: UserPermissionCreate, actor: UUID) -> UserPermissionResponse:
        found = await self._policies.get_by_external_id(data.policy_id)
        policy = require(found, "Policy", data.policy_id)
        if policy.status is not Status.ACTIVE:
            raise ConflictError(f"Policy {policy.external_id} is inactive")
        check_resource_allowed(PermissionName(policy.permission_name), data.resource_type)

        await self._require_exists(data.entity_type, data.entity_id)
        if data.resource_type is not ResourceType.ALL:
            await self._require_exists(data.resource_type, UUID(str(data.resource_id)))

        grant = UserPermission(
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            policy_id=policy.id,
            resource_type=data.resource_type,
            resource_id=str(data.resource_id),
            created_by=actor,
            updated_by=actor,
        )
        self._user_permissions.add(grant)
        await commit_or_conflict(self._session, "This permission is already granted")
        return UserPermissionResponse.from_model(grant, policy.external_id)

    async def update(
        self, grant_id: UUID, data: UserPermissionUpdate, actor: UUID
    ) -> UserPermissionResponse:
        grant = require(
            await self._user_permissions.get_by_external_id(grant_id), "User permission", grant_id
        )
        policy: Policy = await self._policies.get(grant.policy_id)
        if data.status is Status.ACTIVE and policy.status is not Status.ACTIVE:
            raise ConflictError("Policy is inactive; activate it first")
        grant.mark_status(data.status, actor)
        await self._session.commit()
        return UserPermissionResponse.from_model(grant, policy.external_id)

    async def _require_exists(self, kind: str, external_id: UUID) -> None:
        # False = owner says it is missing. None = nobody can answer yet, accept unverified.
        if await self._verifier.exists(kind, external_id) is False:
            raise NotFoundError(f"{kind} {external_id} not found")
