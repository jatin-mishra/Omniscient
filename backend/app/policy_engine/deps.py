from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db_session
from app.entity_verifier import SqlEntityVerifier
from app.policy_engine.core.policy_service import PolicyService
from app.policy_engine.core.user_permission_service import UserPermissionService
from app.policy_engine.repositories.policy_repository import PolicyRepository
from app.policy_engine.repositories.user_permission_repository import UserPermissionRepository

Session = Annotated[AsyncSession, Depends(get_db_session)]


def get_policy_service(session: Session) -> PolicyService:
    return PolicyService(session, PolicyRepository(session), UserPermissionRepository(session))


def get_user_permission_service(session: Session) -> UserPermissionService:
    return UserPermissionService(
        session,
        PolicyRepository(session),
        UserPermissionRepository(session),
        SqlEntityVerifier(session),
    )
