from typing import Protocol
from uuid import UUID


class EntityVerifier(Protocol):
    """Asks whoever owns an entity whether it exists. Implemented at the root layer so
    policy_engine never imports another module."""

    async def exists(self, kind: str, external_id: UUID) -> bool | None:
        """True / False when known, None when no owner can answer yet (accept unverified)."""
        ...
