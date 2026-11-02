from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.retrieval.schemas.common import StrictModel

LogMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class LogWorkflowRequest(StrictModel):
    message: LogMessage


class WorkflowAccepted(BaseModel):
    workflow_id: str
