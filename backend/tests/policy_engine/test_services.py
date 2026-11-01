"""Business rules (ids refer to metric/test_cases_and_metrics.yml, policy_engine section)."""

from uuid import uuid4

import pytest

from app.constants.permissions import PermissionName as P
from app.constants.permissions import ResourceType
from app.constants.status import Status
from app.errors import ConflictError, InvalidRequestError, NotFoundError
from app.policy_engine.models import Effect, EntityType
from app.policy_engine.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate
from app.policy_engine.schemas.user_permission import UserPermissionCreate, UserPermissionUpdate
from tests.policy_engine.fakes import FakeDb

ACTOR = uuid4()
ALL = "ALL"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


async def new_policy(
    db: FakeDb, perm: P = P.TEAM_UPDATE, effect: Effect = Effect.ALLOW
) -> PolicyResponse:
    return await db.policies.create(PolicyCreate(permission_name=perm, effect=effect), ACTOR)


def grant_body(db: FakeDb, policy: PolicyResponse, **over: object) -> UserPermissionCreate:
    fields: dict[str, object] = {
        "entity_type": EntityType.TEAM,
        "entity_id": db.verifier.add("team"),
        "policy_id": policy.id,
        "resource_type": ResourceType.ALL,
        "resource_id": ALL,
    }
    return UserPermissionCreate(**{**fields, **over})


async def test_policy_create_sets_actor_and_active(db: FakeDb) -> None:  # HP-1
    policy = await new_policy(db)
    assert policy.status is Status.ACTIVE
    assert policy.created_by == policy.updated_by == ACTOR


async def test_policy_status_update_records_actor(db: FakeDb) -> None:  # HP-2, P10
    policy = await new_policy(db)
    other = uuid4()
    res = await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), other)
    assert (res.status, res.updated_by, res.created_by) == (Status.INACTIVE, other, ACTOR)
    again = await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), other)
    assert again.status is Status.INACTIVE


async def test_policy_update_unknown_is_404(db: FakeDb) -> None:  # P7
    with pytest.raises(NotFoundError):
        await db.policies.update(uuid4(), PolicyUpdate(status=Status.ACTIVE), ACTOR)


async def test_cannot_deactivate_policy_with_active_grants(db: FakeDb) -> None:  # P9
    policy = await new_policy(db)
    grant = await db.grants.create(grant_body(db, policy), ACTOR)
    with pytest.raises(ConflictError):
        await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), ACTOR)
    await db.grants.update(grant.id, UserPermissionUpdate(status=Status.INACTIVE), ACTOR)
    await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), ACTOR)


async def test_grant_all_scope(db: FakeDb) -> None:  # HP-3, E5
    policy = await new_policy(db)
    res = await db.grants.create(grant_body(db, policy), ACTOR)
    assert res.resource_id == ALL and res.policy_id == policy.id and res.created_by == ACTOR
    assert [k for k, _ in db.verifier.calls] == ["team"]  # only the entity, no resource lookup


async def test_directory_scope_is_accepted_unverified(db: FakeDb) -> None:  # HP-4, E6
    policy = await new_policy(db, P.DIRECTORY_READ)
    for rtype in (ResourceType.DIRECTORY, ResourceType.TEAM):
        rid = db.verifier.add("team") if rtype is ResourceType.TEAM else uuid4()
        await db.grants.create(grant_body(db, policy, resource_type=rtype, resource_id=rid), ACTOR)


@pytest.mark.parametrize(
    "rtype", [ResourceType.DIRECTORY, ResourceType.DOCUMENT, ResourceType.PANEL]
)
async def test_unverifiable_resource_kinds_pass(db: FakeDb, rtype: ResourceType) -> None:  # E6
    policy = await new_policy(
        db, P.DOCUMENT_READ if rtype is not ResourceType.PANEL else P.PANEL_UPDATE
    )
    await db.grants.create(grant_body(db, policy, resource_type=rtype, resource_id=uuid4()), ACTOR)


@pytest.mark.parametrize(
    ("perm", "rtype"),
    [
        (P.USER_UPDATE, ResourceType.TEAM),  # R4
        (P.TEAM_CREATE, ResourceType.TEAM),  # R5
        (P.TEAM_ADD_USER, ResourceType.TEAM),  # R5
        (P.DIRECTORY_CREATE, ResourceType.DIRECTORY),  # R7
        (P.TEAM_UPDATE, ResourceType.DOCUMENT),  # R9
    ],
)
async def test_scope_not_allowed_for_permission(db: FakeDb, perm: P, rtype: ResourceType) -> None:
    policy = await new_policy(db, perm)
    with pytest.raises(InvalidRequestError):
        await db.grants.create(
            grant_body(db, policy, resource_type=rtype, resource_id=db.verifier.add("team")), ACTOR
        )


@pytest.mark.parametrize(
    "rtype", [ResourceType.TEAM, ResourceType.DIRECTORY, ResourceType.DOCUMENT]
)
async def test_document_permission_accepts_each_scope(
    db: FakeDb, rtype: ResourceType
) -> None:  # R8
    policy = await new_policy(db, P.DOCUMENT_DELETE)
    rid = db.verifier.add("team") if rtype is ResourceType.TEAM else uuid4()
    await db.grants.create(grant_body(db, policy, resource_type=rtype, resource_id=rid), ACTOR)


async def test_unknown_policy_is_404(db: FakeDb) -> None:  # E1
    policy = await new_policy(db)
    body = grant_body(db, policy, policy_id=uuid4())
    with pytest.raises(NotFoundError):
        await db.grants.create(body, ACTOR)


async def test_inactive_policy_is_409(db: FakeDb) -> None:  # E2
    policy = await new_policy(db)
    await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), ACTOR)
    with pytest.raises(ConflictError):
        await db.grants.create(grant_body(db, policy), ACTOR)


@pytest.mark.parametrize("etype", list(EntityType))
async def test_unknown_entity_is_404(db: FakeDb, etype: EntityType) -> None:  # E3
    policy = await new_policy(db)
    with pytest.raises(NotFoundError):
        await db.grants.create(grant_body(db, policy, entity_type=etype, entity_id=uuid4()), ACTOR)


async def test_unknown_team_resource_is_404(db: FakeDb) -> None:  # E4
    policy = await new_policy(db)
    with pytest.raises(NotFoundError):
        await db.grants.create(
            grant_body(db, policy, resource_type=ResourceType.TEAM, resource_id=uuid4()), ACTOR
        )


async def test_reactivating_grant_under_inactive_policy_is_409(db: FakeDb) -> None:  # E8
    policy = await new_policy(db)
    grant = await db.grants.create(grant_body(db, policy), ACTOR)
    await db.grants.update(grant.id, UserPermissionUpdate(status=Status.INACTIVE), ACTOR)  # HP-5
    await db.policies.update(policy.id, PolicyUpdate(status=Status.INACTIVE), ACTOR)
    with pytest.raises(ConflictError):
        await db.grants.update(grant.id, UserPermissionUpdate(status=Status.ACTIVE), ACTOR)


async def test_update_unknown_grant_is_404(db: FakeDb) -> None:  # E9
    with pytest.raises(NotFoundError):
        await db.grants.update(uuid4(), UserPermissionUpdate(status=Status.ACTIVE), ACTOR)


async def test_same_entity_and_policy_different_resource_allowed(db: FakeDb) -> None:  # E10
    policy = await new_policy(db)
    body = grant_body(db, policy)
    await db.grants.create(body, ACTOR)
    other = body.model_copy(
        update={"resource_type": ResourceType.TEAM, "resource_id": db.verifier.add("team")}
    )
    await db.grants.create(other, ACTOR)
