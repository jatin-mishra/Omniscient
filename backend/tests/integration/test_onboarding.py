"""Onboarding against real Postgres (ids refer to metric/test_cases_and_metrics.yml).
Rows are committed (the API owns its transactions), so every name/email carries a unique tag."""

import asyncio
from collections.abc import Iterator, Mapping
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import get_settings
from app.db.postgres import create_db, create_tables
from app.errors import ConflictError
from app.main import app
from app.onboarding.core.group_service import GroupService
from app.onboarding.models import Group
from app.onboarding.repositories.group_repository import GroupRepository
from app.onboarding.schemas.group import GroupCreate, GroupResponse

pytestmark = pytest.mark.integration


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # Exercise the real startup path: lifespan creates the schema.
    monkeypatch.setenv("CREATE_SCHEMA_ON_STARTUP", "true")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
def tag() -> str:
    return uuid4().hex[:10]


def post(
    api: TestClient, path: str, body: Mapping[str, object], expected: int = 201
) -> dict[str, str]:
    res = api.post(path, json=body)
    assert res.status_code == expected, res.text
    data: dict[str, str] = res.json()
    return data


async def count_groups_named(name: str) -> int:
    engine, sessionmaker = create_db(get_settings())
    async with sessionmaker() as session:
        n = await session.scalar(
            select(func.count()).select_from(Group).where(func.lower(Group.name) == name.lower())
        )
    await engine.dispose()
    return n or 0


def test_full_flow_round_trips(api: TestClient, tag: str) -> None:  # HP-1, HP-2, HP-5
    team = post(api, "/v1/teams", {"name": f"team-{tag}"})
    user = post(api, "/v1/users", {"name": "Ann", "email": f"{tag}@x.io", "team_id": team["id"]})
    group = post(api, "/v1/groups", {"name": f"group-{tag}"})
    membership = post(api, "/v1/group-users", {"group_id": group["id"], "user_id": user["id"]})
    patched = api.patch(f"/v1/teams/{team['id']}", json={"manager_id": user["id"]}).json()
    assert patched["manager_id"] == user["id"]

    for path, body in [
        (f"/v1/teams/{team['id']}", patched),
        (f"/v1/users/{user['id']}", user),
        (f"/v1/groups/{group['id']}", group),
        (f"/v1/group-users/{membership['id']}", membership),
    ]:
        fetched = api.get(path).json()
        assert fetched == body
        assert "external_id" not in fetched
        assert not any(isinstance(v, int) for v in fetched.values())  # no internal BIGINT id


def test_unique_names_and_email_are_case_insensitive(api: TestClient, tag: str) -> None:
    team = post(api, "/v1/teams", {"name": f"Team-{tag}"})
    post(api, "/v1/teams", {"name": f"TEAM-{tag}"}, expected=409)  # case 4
    post(api, "/v1/groups", {"name": f"Group-{tag}"})
    post(api, "/v1/groups", {"name": f"group-{tag}"}, expected=409)  # case 12
    post(api, "/v1/users", {"name": "A", "email": f"{tag}@x.io", "team_id": team["id"]})
    post(api, "/v1/users", {"name": "B", "email": f"{tag}@X.IO", "team_id": team["id"]}, 409)  # 8


def test_rename_to_taken_name_is_409(api: TestClient, tag: str) -> None:  # case 4 via PATCH
    post(api, "/v1/teams", {"name": f"a-{tag}"})
    other = post(api, "/v1/teams", {"name": f"b-{tag}"})
    assert api.patch(f"/v1/teams/{other['id']}", json={"name": f"A-{tag}"}).status_code == 409


def test_duplicate_membership_even_inactive_is_409(api: TestClient, tag: str) -> None:  # 14
    team = post(api, "/v1/teams", {"name": f"team-{tag}"})
    user = post(api, "/v1/users", {"name": "A", "email": f"{tag}@x.io", "team_id": team["id"]})
    group = post(api, "/v1/groups", {"name": f"group-{tag}"})
    body = {"group_id": group["id"], "user_id": user["id"]}
    membership = post(api, "/v1/group-users", body)
    api.patch(f"/v1/group-users/{membership['id']}", json={"status": "INACTIVE"})
    post(api, "/v1/group-users", body, expected=409)


def test_failed_request_leaves_no_partial_rows(api: TestClient, tag: str) -> None:  # case 17
    post(api, "/v1/groups", {"name": f"g-{tag}"})
    post(api, "/v1/groups", {"name": f"G-{tag}"}, expected=409)
    assert asyncio.run(count_groups_named(f"g-{tag}")) == 1
    post(api, "/v1/groups", {"name": f"other-{tag}"})  # app still healthy after the rollback


def test_updated_at_moves_on_patch_created_at_does_not(api: TestClient, tag: str) -> None:  # 18
    team = post(api, "/v1/teams", {"name": f"t-{tag}"})
    patched = api.patch(f"/v1/teams/{team['id']}", json={"name": f"t2-{tag}"}).json()
    assert patched["created_at"] == team["created_at"]
    assert patched["updated_at"] > team["updated_at"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_duplicate_create_is_one_201_one_409(tag: str) -> None:  # case 16
    engine, sessionmaker = create_db(get_settings())
    await create_tables(engine)

    async def create() -> GroupResponse:
        async with sessionmaker() as session:
            service = GroupService(session, GroupRepository(session))
            return await service.create(GroupCreate(name=f"race-{tag}"))

    results = await asyncio.gather(create(), create(), return_exceptions=True)
    await engine.dispose()
    assert sorted(type(r).__name__ for r in results) == ["ConflictError", "GroupResponse"]
    assert any(isinstance(r, ConflictError) for r in results)
