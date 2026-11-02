import logging

from temporalio import activity

log = logging.getLogger(__name__)


@activity.defn
async def log_activity(message: str) -> None:
    log.info("workflow %s: %s", activity.info().workflow_id, message)
