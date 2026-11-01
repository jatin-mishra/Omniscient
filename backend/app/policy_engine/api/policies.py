from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.policy_engine.core.policy_service import PolicyService
from app.policy_engine.deps import get_policy_service
from app.policy_engine.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])

Service = Annotated[PolicyService, Depends(get_policy_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_policy(body: PolicyCreate, service: Service, actor: Actor) -> PolicyResponse:
    return await service.create(body, actor)


@router.patch("/{policy_id}")
async def update_policy(
    policy_id: UUID, body: PolicyUpdate, service: Service, actor: Actor
) -> PolicyResponse:
    return await service.update(policy_id, body, actor)
