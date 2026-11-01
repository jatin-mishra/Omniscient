from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.onboarding.core.user_service import UserService
from app.onboarding.deps import get_user_service
from app.onboarding.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

Service = Annotated[UserService, Depends(get_user_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, service: Service) -> UserResponse:
    return await service.create(body)


@router.get("/{user_id}")
async def get_user(user_id: UUID, service: Service) -> UserResponse:
    return await service.get(user_id)


@router.patch("/{user_id}")
async def update_user(user_id: UUID, body: UserUpdate, service: Service) -> UserResponse:
    return await service.update(user_id, body)
