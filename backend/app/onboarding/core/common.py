from app.db.helpers import commit_or_conflict, require
from app.errors import ConflictError
from app.onboarding.models import Group, Status, Team, User

__all__ = ["commit_or_conflict", "require", "require_active"]


def require_active(entity: Team | User | Group, label: str) -> None:
    if entity.status is not Status.ACTIVE:
        raise ConflictError(f"{label} {entity.external_id} is inactive")
