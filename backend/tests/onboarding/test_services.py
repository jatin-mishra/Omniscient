"""Business rules (ids refer to metric/test_cases_and_metrics.yml)."""

from uuid import uuid4

import pytest

from app.errors import ConflictError, NotFoundError
from app.onboarding.models import Status
from app.onboarding.schemas.group import GroupCreate, GroupUpdate
from app.onboarding.schemas.group_user import GroupUserCreate, GroupUserUpdate
from app.onboarding.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.onboarding.schemas.user import UserCreate, UserResponse, UserUpdate
from tests.onboarding.fakes import FakeDb

ACTIVE, INACTIVE = Status.ACTIVE, Status.INACTIVE


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


async def new_team(db: FakeDb, name: str = "core") -> TeamResponse:
    return await db.teams.create(TeamCreate(name=name))


async def new_user(db: FakeDb, team: TeamResponse, email: str = "a@x.io") -> UserResponse:
    return await db.users.create(UserCreate(name="Ann", email=email, team_id=team.id))


pytestmark = pytest.mark.anyio


async def test_create_defaults_to_active_and_get_round_trips(db: FakeDb) -> None:  # HP-1, HP-2
    team = await new_team(db)
    user = await new_user(db, team)
    assert (team.status, user.status) == (ACTIVE, ACTIVE)
    assert await db.teams.get(team.id) == team
    assert await db.users.get(user.id) == user


async def test_email_is_stored_lowercase(db: FakeDb) -> None:  # supports case 8
    user = await db.users.create(
        UserCreate(name="A", email="Ann@X.io", team_id=(await new_team(db)).id)
    )
    assert user.email == "ann@x.io"


async def test_empty_patch_changes_nothing(db: FakeDb) -> None:  # HP-4
    team = await new_team(db)
    assert await db.teams.update(team.id, TeamUpdate()) == team


async def test_patch_one_field_changes_only_that_field(db: FakeDb) -> None:  # HP-3
    team = await new_team(db)
    updated = await db.teams.update(team.id, TeamUpdate(name="platform"))
    assert updated.model_dump(exclude={"name"}) == team.model_dump(exclude={"name"})
    assert updated.name == "platform"


@pytest.mark.parametrize("service", ["teams", "users", "groups", "memberships"])
async def test_unknown_id_is_not_found(db: FakeDb, service: str) -> None:  # case 1
    with pytest.raises(NotFoundError):
        await getattr(db, service).get(uuid4())


# --- teams ---


async def test_unknown_manager_is_not_found(db: FakeDb) -> None:  # case 5
    with pytest.raises(NotFoundError):
        await db.teams.create(TeamCreate(name="t", manager_id=uuid4()))


async def test_inactive_manager_is_conflict(db: FakeDb) -> None:  # case 5
    user = await new_user(db, await new_team(db))
    await db.users.update(user.id, UserUpdate(status=INACTIVE))
    with pytest.raises(ConflictError):
        await db.teams.create(TeamCreate(name="t2", manager_id=user.id))


async def test_deactivate_team_with_active_users_is_conflict(db: FakeDb) -> None:  # case 6
    team = await new_team(db)
    user = await new_user(db, team)
    with pytest.raises(ConflictError):
        await db.teams.update(team.id, TeamUpdate(status=INACTIVE))
    await db.users.update(user.id, UserUpdate(status=INACTIVE))  # only inactive users left
    assert (await db.teams.update(team.id, TeamUpdate(status=INACTIVE))).status == INACTIVE


async def test_set_and_clear_manager(db: FakeDb) -> None:  # case 7
    team = await new_team(db)
    user = await new_user(db, team)
    assert (await db.teams.update(team.id, TeamUpdate(manager_id=user.id))).manager_id == user.id
    assert (await db.teams.update(team.id, TeamUpdate(manager_id=None))).manager_id is None


async def test_reactivate_team_with_inactive_manager(db: FakeDb) -> None:  # case B
    home = await new_team(db, "home")
    manager = await new_user(db, home)
    team = await db.teams.create(TeamCreate(name="managed", manager_id=manager.id))
    await db.teams.update(team.id, TeamUpdate(status=INACTIVE))
    await db.users.update(manager.id, UserUpdate(status=INACTIVE))  # allowed: team is inactive
    with pytest.raises(ConflictError):
        await db.teams.update(team.id, TeamUpdate(status=ACTIVE))
    # same PATCH clears the manager -> allowed
    reactivated = await db.teams.update(team.id, TeamUpdate(status=ACTIVE, manager_id=None))
    assert (reactivated.status, reactivated.manager_id) == (ACTIVE, None)


# --- users ---


async def test_user_in_unknown_or_inactive_team(db: FakeDb) -> None:  # case 9
    with pytest.raises(NotFoundError):
        await db.users.create(UserCreate(name="A", email="a@x.io", team_id=uuid4()))
    closed = await new_team(db, "closed")
    await db.teams.update(closed.id, TeamUpdate(status=INACTIVE))
    with pytest.raises(ConflictError):
        await db.users.create(UserCreate(name="A", email="a@x.io", team_id=closed.id))
    user = await new_user(db, await new_team(db, "open"))
    with pytest.raises(ConflictError):  # move into an inactive team
        await db.users.update(user.id, UserUpdate(team_id=closed.id))


async def test_deactivate_manager_of_active_team_is_conflict(db: FakeDb) -> None:  # case 10
    team = await new_team(db)
    user = await new_user(db, team)
    await db.teams.update(team.id, TeamUpdate(manager_id=user.id))
    with pytest.raises(ConflictError):
        await db.users.update(user.id, UserUpdate(status=INACTIVE))


async def test_reactivate_user_in_inactive_team(db: FakeDb) -> None:  # case A
    team = await new_team(db, "old")
    user = await new_user(db, team)
    await db.users.update(user.id, UserUpdate(status=INACTIVE))
    await db.teams.update(team.id, TeamUpdate(status=INACTIVE))
    with pytest.raises(ConflictError):
        await db.users.update(user.id, UserUpdate(status=ACTIVE))
    # same PATCH moves them to an active team -> allowed
    other = await new_team(db, "new")
    moved = await db.users.update(user.id, UserUpdate(status=ACTIVE, team_id=other.id))
    assert (moved.status, moved.team_id) == (ACTIVE, other.id)


# --- groups / memberships ---


async def test_deactivating_group_is_always_allowed(db: FakeDb) -> None:  # case 12
    group = await db.groups.create(GroupCreate(name="sre"))
    user = await new_user(db, await new_team(db))
    await db.memberships.create(GroupUserCreate(group_id=group.id, user_id=user.id))
    assert (await db.groups.update(group.id, GroupUpdate(status=INACTIVE))).status == INACTIVE


async def test_membership_needs_known_active_group_and_user(db: FakeDb) -> None:  # case 13
    group = await db.groups.create(GroupCreate(name="sre"))
    user = await new_user(db, await new_team(db))
    with pytest.raises(NotFoundError):
        await db.memberships.create(GroupUserCreate(group_id=uuid4(), user_id=user.id))
    with pytest.raises(NotFoundError):
        await db.memberships.create(GroupUserCreate(group_id=group.id, user_id=uuid4()))
    await db.users.update(user.id, UserUpdate(status=INACTIVE))
    with pytest.raises(ConflictError):
        await db.memberships.create(GroupUserCreate(group_id=group.id, user_id=user.id))
    await db.groups.update(group.id, GroupUpdate(status=INACTIVE))
    await db.users.update(user.id, UserUpdate(status=ACTIVE))
    with pytest.raises(ConflictError):
        await db.memberships.create(GroupUserCreate(group_id=group.id, user_id=user.id))


async def test_reactivate_membership_of_inactive_group(db: FakeDb) -> None:  # case 15
    group = await db.groups.create(GroupCreate(name="sre"))
    user = await new_user(db, await new_team(db))
    membership = await db.memberships.create(GroupUserCreate(group_id=group.id, user_id=user.id))
    await db.memberships.update(membership.id, GroupUserUpdate(status=INACTIVE))
    await db.groups.update(group.id, GroupUpdate(status=INACTIVE))
    with pytest.raises(ConflictError):
        await db.memberships.update(membership.id, GroupUserUpdate(status=ACTIVE))
    fetched = await db.memberships.get(membership.id)
    assert (fetched.group_id, fetched.user_id, fetched.status) == (group.id, user.id, INACTIVE)
