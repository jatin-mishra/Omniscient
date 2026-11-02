"""policy_engine against real Postgres (ids refer to metric/test_cases_and_metrics.yml).
Rows are committed and (permission, effect) is globally unique, so a policy left by an earlier
run is looked up and reused; teams and grants use fresh ids every run."""

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.db.postgres import create_db
from app.main import app
from app.policy_engine.models import Policy

pytestmark = pytest.mark.integration

H = {"X-User-Id": str(uuid4())}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CREATE_SCHEMA_ON_STARTUP", "true")  # I1: schema made at startup
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


async def _reset_policy(perm: str, effect: str) -> None:
    """Re-activate a leftover policy (deactivated by an earlier run) so tests can use it."""
    engine, sessionmaker = create_db(get_settings())
    async with sessionmaker() as session:
        policy = await session.scalar(
            select(Policy).where(Policy.permission_name == perm, Policy.effect == effect)
        )
        if policy is not None:
            policy.status = "ACTIVE"  # type: ignore[assignment]
            await session.commit()
    await engine.dispose()


def active_policy(api: TestClient, perm: str, effect: str = "ALLOW") -> str:
    asyncio.run(_reset_policy(perm, effect))
    res = api.post("/v1/policies", json={"permission_name": perm, "effect": effect}, headers=H)
    if res.status_code == 201:
        return str(res.json()["id"])
    assert res.status_code == 409, res.text  # P3: the DB constraint rejected the duplicate
    return asyncio.run(_policy_id(perm, effect))


async def _policy_id(perm: str, effect: str) -> str:
    engine, sessionmaker = create_db(get_settings())
    async with sessionmaker() as session:
        policy = await session.scalar(
            select(Policy).where(Policy.permission_name == perm, Policy.effect == effect)
        )
    await engine.dispose()
    assert policy is not None
    return str(policy.external_id)


def patch(api: TestClient, path: str, status: str) -> int:
    return api.patch(path, json={"status": status}, headers=H).status_code


def test_end_to_end_flow(api: TestClient) -> None:  # I2, E7, P9
    team = api.post("/v1/teams", json={"name": f"team-{uuid4().hex[:10]}"}).json()
    policy_id = active_policy(api, "team:update")
    body = {
        "entity_type": "team",
        "entity_id": team["id"],
        "policy_id": policy_id,
        "resource_type": "team",
        "resource_id": team["id"],
    }
    grant = api.post("/v1/user-permissions", json=body, headers=H)
    assert grant.status_code == 201, grant.text
    assert api.post("/v1/user-permissions", json=body, headers=H).status_code == 409  # E7

    gid = grant.json()["id"]
    assert patch(api, f"/v1/policies/{policy_id}", "INACTIVE") == 409  # P9
    assert patch(api, f"/v1/user-permissions/{gid}", "INACTIVE") == 200
    assert patch(api, f"/v1/policies/{policy_id}", "INACTIVE") == 200


def test_duplicate_policy_is_409(api: TestClient) -> None:  # P3, I1
    active_policy(api, "user:create", "DENY")
    res = api.post(
        "/v1/policies", json={"permission_name": "user:create", "effect": "DENY"}, headers=H
    )
    assert res.status_code == 409


def test_unknown_team_scope_is_404(api: TestClient) -> None:  # E3, E4 against real tables
    policy_id = active_policy(api, "team:update")
    body = {
        "entity_type": "user",
        "entity_id": str(uuid4()),
        "policy_id": policy_id,
        "resource_type": "ALL",
        "resource_id": "ALL",
    }
    assert api.post("/v1/user-permissions", json=body, headers=H).status_code == 404


def test_concurrent_duplicate_grant_never_500(api: TestClient) -> None:  # I3
    team = api.post("/v1/teams", json={"name": f"team-{uuid4().hex[:10]}"}).json()
    body = {
        "entity_type": "team",
        "entity_id": team["id"],
        "policy_id": active_policy(api, "team:delete"),
        "resource_type": "ALL",
        "resource_id": "ALL",
    }

    def post(_: int) -> int:
        return api.post("/v1/user-permissions", json=body, headers=H).status_code

    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(post, range(2)))
    assert codes == [201, 409]
