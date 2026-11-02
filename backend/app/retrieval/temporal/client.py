import logging
from datetime import timedelta

from temporalio.client import Client

from app.config import Settings

log = logging.getLogger(__name__)


async def create_temporal_client(settings: Settings, *, lazy: bool = True) -> Client:
    """Lazy (default): no connection is opened, so the API boots even when Temporal is down and
    the first RPC connects. Workers need `lazy=False` (the SDK rejects lazy clients for them).
    The SDK client has no close(); the owner just drops it."""
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        api_key=settings.temporal_api_key or None,
        tls=settings.temporal_tls,
        connect_timeout=timedelta(seconds=settings.temporal_connect_timeout_s),
        lazy=lazy,
    )


async def ping_temporal(client: Client, timeout_s: float) -> bool:
    try:
        return await client.service_client.check_health(timeout=timedelta(seconds=timeout_s))
    except Exception as exc:  # the SDK raises RPCError, RuntimeError or timeouts; all mean down
        log.warning("temporal ping failed: %s", exc)
        return False
