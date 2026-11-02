from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.onboarding.core.group_service import GroupService
from app.onboarding.deps import get_group_service
from app.onboarding.schemas.group import GroupCreate, GroupResponse, GroupUpdate

router = APIRouter(prefix="/groups", tags=["groups"])

Service = Annotated[GroupService, Depends(get_group_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(body: GroupCreate, service: Service) -> GroupResponse:
    return await service.create(body)


@router.get("/{group_id}")
async def get_group(group_id: UUID, service: Service) -> GroupResponse:
    return await service.get(group_id)


@router.patch("/{group_id}")
async def update_group(group_id: UUID, body: GroupUpdate, service: Service) -> GroupResponse:
    return await service.update(group_id, body)
