from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.onboarding.core.team_service import TeamService
from app.onboarding.deps import get_team_service
from app.onboarding.schemas.team import TeamCreate, TeamResponse, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])

Service = Annotated[TeamService, Depends(get_team_service)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(body: TeamCreate, service: Service) -> TeamResponse:
    return await service.create(body)


@router.get("/{team_id}")
async def get_team(team_id: UUID, service: Service) -> TeamResponse:
    return await service.get(team_id)


@router.patch("/{team_id}")
async def update_team(team_id: UUID, body: TeamUpdate, service: Service) -> TeamResponse:
    return await service.update(team_id, body)
