# The generic repository now lives in the global layer; re-exported for onboarding.
from app.db.repository import Repository

__all__ = ["Repository"]
