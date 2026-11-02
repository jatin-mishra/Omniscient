from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.retrieval.temporal.activities import log_activity


@workflow.defn
class LogWorkflow:
    """No I/O or logging here (workflows must be deterministic): the activity does the logging."""

    @workflow.run
    async def run(self, message: str) -> None:
        await workflow.execute_activity(
            log_activity, message, start_to_close_timeout=timedelta(seconds=10)
        )
