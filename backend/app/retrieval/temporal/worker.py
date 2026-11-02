"""Worker process: `python -m app.retrieval.temporal.worker`. Runs until SIGINT/SIGTERM."""

import asyncio
import logging
import signal

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import Settings, get_settings
from app.logging import configure_logging
from app.retrieval.temporal.activities import log_activity
from app.retrieval.temporal.client import create_temporal_client
from app.retrieval.temporal.workflows import LogWorkflow

log = logging.getLogger(__name__)


def build_worker(client: Client, settings: Settings) -> Worker:
    return Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[LogWorkflow],
        activities=[log_activity],
    )


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    worker = build_worker(await create_temporal_client(settings, lazy=False), settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    log.info("worker started on task queue %s", settings.temporal_task_queue)
    async with worker:  # entering starts polling; leaving drains in-flight tasks
        await stop.wait()
    log.info("worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
