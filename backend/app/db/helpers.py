from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError


def require[T](entity: T | None, label: str, external_id: UUID) -> T:
    if entity is None:
        raise NotFoundError(f"{label} {external_id} not found")
    return entity


async def commit_or_conflict(session: AsyncSession, message: str) -> None:
    """Commit; a unique-constraint violation (e.g. a concurrent duplicate) becomes a 409."""
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(message) from exc
