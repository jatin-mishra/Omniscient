from datetime import timedelta
from uuid import uuid4

from temporalio.client import Client

from app.retrieval.errors import WorkflowUnavailableError
from app.retrieval.schemas.workflow import WorkflowAccepted
from app.retrieval.temporal.workflows import LogWorkflow


class WorkflowService:
    def __init__(
        self,
        client: Client,
        task_queue: str,
        execution_timeout: timedelta,
        rpc_timeout: timedelta,
    ) -> None:
        self._client = client
        self._task_queue = task_queue
        self._execution_timeout = execution_timeout
        self._rpc_timeout = rpc_timeout

    async def trigger_log(self, message: str) -> WorkflowAccepted:
        """Starts the workflow and returns without waiting for it to finish."""
        workflow_id = f"log-{uuid4()}"
        try:
            await self._client.start_workflow(
                LogWorkflow.run,
                message,
                id=workflow_id,
                task_queue=self._task_queue,
                execution_timeout=self._execution_timeout,
                rpc_timeout=self._rpc_timeout,
            )
        except Exception as exc:  # RPCError, RuntimeError (connect failed), TimeoutError, ...
            raise WorkflowUnavailableError("Workflow engine is unavailable") from exc
        return WorkflowAccepted(workflow_id=workflow_id)
