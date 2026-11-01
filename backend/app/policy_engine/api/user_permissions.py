from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.policy_engine.core.user_permission_service import UserPermissionService
from app.policy_engine.deps import get_user_permission_service
from app.policy_engine.schemas.user_permission import (
    UserPermissionCreate,
    UserPermissionResponse,
    UserPermissionUpdate,
)

router = APIRouter(prefix="/user-permissions", tags=["user-permissions"])

Service = Annotated[UserPermissionService, Depends(get_user_permission_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user_permission(
    body: UserPermissionCreate, service: Service, actor: Actor
) -> UserPermissionResponse:
    return await service.create(body, actor)


@router.patch("/{grant_id}")
async def update_user_permission(
    grant_id: UUID, body: UserPermissionUpdate, service: Service, actor: Actor
) -> UserPermissionResponse:
    return await service.update(grant_id, body, actor)
