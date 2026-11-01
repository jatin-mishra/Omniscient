from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.onboarding.core.group_user_service import GroupUserService
from app.onboarding.deps import get_group_user_service
from app.onboarding.schemas.group_user import GroupUserCreate, GroupUserResponse, GroupUserUpdate

router = APIRouter(prefix="/group-users", tags=["group-users"])

Service = Annotated[GroupUserService, Depends(get_group_user_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_membership(body: GroupUserCreate, service: Service) -> GroupUserResponse:
    return await service.create(body)


@router.get("/{membership_id}")
async def get_membership(membership_id: UUID, service: Service) -> GroupUserResponse:
    return await service.get(membership_id)


@router.patch("/{membership_id}")
async def update_membership(
    membership_id: UUID, body: GroupUserUpdate, service: Service
) -> GroupUserResponse:
    return await service.update(membership_id, body)
