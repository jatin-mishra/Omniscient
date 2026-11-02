from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import get_actor
from app.retrieval.core.workflow_service import WorkflowService
from app.retrieval.deps import get_workflow_service
from app.retrieval.schemas.workflow import LogWorkflowRequest, WorkflowAccepted

router = APIRouter(prefix="/workflows", tags=["workflows"])

Service = Annotated[WorkflowService, Depends(get_workflow_service)]
Actor = Annotated[UUID, Depends(get_actor)]


@router.post("/log", status_code=status.HTTP_202_ACCEPTED)
async def trigger_log_workflow(
    body: LogWorkflowRequest, service: Service, _: Actor
) -> WorkflowAccepted:
    return await service.trigger_log(body.message)
