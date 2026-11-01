from uuid import UUID, uuid4

from app.constants.status import Status
from app.policy_engine.core.policy_service import PolicyService
from app.policy_engine.core.user_permission_service import UserPermissionService
from app.policy_engine.models import Policy, UserPermission
from tests.onboarding.fakes import FakeRepo, FakeSession


class FakeGrants(FakeRepo[UserPermission]):
    async def find_active_for_policy(self, policy_id: int) -> UserPermission | None:
        return next(
            (g for g in self.rows if g.policy_id == policy_id and g.status is Status.ACTIVE), None
        )


class FakeVerifier:
    """Knows the (kind, id) pairs it was told about. Directory/document/panel are unverifiable."""

    UNVERIFIABLE = {"directory", "document", "panel"}

    def __init__(self) -> None:
        self.known: set[tuple[str, UUID]] = set()
        self.calls: list[tuple[str, UUID]] = []

    def add(self, kind: str) -> UUID:
        id_ = uuid4()
        self.known.add((kind, id_))
        return id_

    async def exists(self, kind: str, external_id: UUID) -> bool | None:
        self.calls.append((kind, external_id))
        if kind in self.UNVERIFIABLE:
            return None
        return (kind, external_id) in self.known


class FakeDb:
    def __init__(self) -> None:
        session = FakeSession()
        self.verifier = FakeVerifier()
        self.policies_repo = FakeRepo[Policy]()
        self.grants_repo = FakeGrants()
        self.policies = PolicyService(session, self.policies_repo, self.grants_repo)  # type: ignore[arg-type]
        self.grants = UserPermissionService(
            session,  # type: ignore[arg-type]
            self.policies_repo,  # type: ignore[arg-type]
            self.grants_repo,  # type: ignore[arg-type]
            self.verifier,
        )
