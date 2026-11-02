"""Root-layer adapter: the one place that knows which module owns which kind of entity.
policy_engine only sees the `EntityVerifier` protocol it defines."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding import public as onboarding


class SqlEntityVerifier:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, kind: str, external_id: UUID) -> bool | None:
        """True / False when the owning module is known, None when nothing can answer yet
        (panel, directory, document); the caller then accepts the id unverified."""
        if kind in onboarding.KINDS:
            return await onboarding.entity_exists(self._session, kind, external_id)
        return None
