from typing import Annotated
from uuid import UUID

from fastapi import Header

from app.errors import UnauthorizedError


def get_actor(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    """Who is calling, from the `X-User-Id` header. Placeholder until real authentication
    exists; callers depend only on this function, so swapping it needs no other change."""
    if x_user_id is None:
        raise UnauthorizedError("X-User-Id header is required")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise UnauthorizedError("X-User-Id must be a UUID") from None
