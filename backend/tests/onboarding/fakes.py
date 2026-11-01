from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.base import IdMixin
from app.onboarding.core.group_service import GroupService
from app.onboarding.core.group_user_service import GroupUserService
from app.onboarding.core.team_service import TeamService
from app.onboarding.core.user_service import UserService
from app.onboarding.models import Group, GroupUser, Status, Team, User


class FakeSession:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class FakeRepo[M: IdMixin]:
    """In-memory stand-in for Repository: fills the defaults a real INSERT would."""

    def __init__(self) -> None:
        self.rows: list[M] = []

    def add(self, entity: M) -> None:
        now = datetime.now(UTC)
        entity.id = len(self.rows) + 1
        entity.external_id = uuid4()
        entity.status = getattr(entity, "status", None) or Status.ACTIVE  # type: ignore[attr-defined]
        entity.created_at = entity.updated_at = now  # type: ignore[attr-defined]
        self.rows.append(entity)

    async def get(self, id_: int) -> M:
        return next(r for r in self.rows if r.id == id_)

    async def get_by_external_id(self, external_id: UUID) -> M | None:
        return next((r for r in self.rows if r.external_id == external_id), None)


class FakeTeams(FakeRepo[Team]):
    async def find_active_managed_by(self, user_id: int) -> Team | None:
        return next(
            (t for t in self.rows if t.manager_id == user_id and t.status is Status.ACTIVE), None
        )


class FakeUsers(FakeRepo[User]):
    async def find_active_in_team(self, team_id: int) -> User | None:
        return next(
            (u for u in self.rows if u.team_id == team_id and u.status is Status.ACTIVE), None
        )


class FakeDb:
    """Services wired to shared in-memory tables, like one request's session would be."""

    def __init__(self) -> None:
        session = FakeSession()
        self.teams_repo = FakeTeams()
        self.users_repo = FakeUsers()
        groups_repo = FakeRepo[Group]()
        memberships_repo = FakeRepo[GroupUser]()
        self.teams = TeamService(session, self.teams_repo, self.users_repo)  # type: ignore[arg-type]
        self.users = UserService(session, self.users_repo, self.teams_repo)  # type: ignore[arg-type]
        self.groups = GroupService(session, groups_repo)  # type: ignore[arg-type]
        self.memberships = GroupUserService(
            session,  # type: ignore[arg-type]
            memberships_repo,  # type: ignore[arg-type]
            groups_repo,  # type: ignore[arg-type]
            self.users_repo,  # type: ignore[arg-type]
        )
