from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import IdMixin


class Repository[M: IdMixin]:
    """Plain select / insert for one table. Updates are attribute changes flushed on commit.
    Does not commit; the caller owns the transaction."""

    model: type[M]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, entity: M) -> None:
        self._session.add(entity)

    async def get(self, id_: int) -> M:
        """By internal id: only used for FK-guaranteed rows, so a miss is a bug (raises)."""
        result = await self._session.scalars(select(self.model).where(self.model.id == id_))
        return result.one()

    async def get_by_external_id(self, external_id: UUID) -> M | None:
        stmt = select(self.model).where(self.model.external_id == external_id)
        return await self._session.scalar(stmt)
