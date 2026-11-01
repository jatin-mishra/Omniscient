"""HTTP layer only: validation, auth header, status codes. Services are stubbed."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.constants.permissions import PermissionName
from app.constants.status import Status
from app.main import app
from app.policy_engine.deps import get_policy_service, get_user_permission_service
from app.policy_engine.models import Effect
from app.policy_engine.schemas.policy import PolicyResponse

NOW = datetime.now(UTC)
ACTOR = str(uuid4())
H = {"X-User-Id": ACTOR}
POLICY = PolicyResponse(
    id=uuid4(),
    permission_name=PermissionName.TEAM_UPDATE,
    effect=Effect.ALLOW,
    status=Status.ACTIVE,
    created_at=NOW,
    created_by=uuid4(),
    updated_at=NOW,
    updated_by=uuid4(),
)


class StubPolicyService:
    async def create(self, *_: Any) -> PolicyResponse:
        return POLICY

    async def update(self, *_: Any) -> PolicyResponse:
        return POLICY


class NeverCalled:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"service.{name} called for an invalid request")


@pytest.fixture(autouse=True)
def stub_services() -> None:
    app.dependency_overrides[get_policy_service] = NeverCalled
    app.dependency_overrides[get_user_permission_service] = NeverCalled


def test_create_policy_201_hides_internal_id(client: TestClient) -> None:  # HP-1
    app.dependency_overrides[get_policy_service] = StubPolicyService
    res = client.post(
        "/v1/policies", json={"permission_name": "team:update", "effect": "ALLOW"}, headers=H
    )
    assert res.status_code == 201
    assert res.json()["id"] == str(POLICY.id)
    assert "external_id" not in res.json()


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "nope"}])  # A1, A2
def test_missing_or_bad_actor_is_401(client: TestClient, headers: dict[str, str]) -> None:
    res = client.post(
        "/v1/policies", json={"permission_name": "team:update", "effect": "ALLOW"}, headers=headers
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "body",
    [
        {"permission_name": "team:fly", "effect": "ALLOW"},  # P1
        {"permission_name": "team:update", "effect": "MAYBE"},  # P2
        {"permission_name": "team:update", "effect": "ALLOW", "x": 1},  # P4
    ],
)
def test_invalid_policy_create_is_422(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/v1/policies", json=body, headers=H).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"status": None},
        {"status": "BOGUS"},
        {"status": "ACTIVE", "effect": "DENY"},
    ],  # P4-P6, P8
)
def test_invalid_policy_patch_is_422(client: TestClient, body: dict[str, Any]) -> None:
    assert client.patch(f"/v1/policies/{uuid4()}", json=body, headers=H).status_code == 422


def grant(**over: Any) -> dict[str, Any]:
    return {
        "entity_type": "team",
        "entity_id": str(uuid4()),
        "policy_id": str(uuid4()),
        "resource_type": "ALL",
        "resource_id": "ALL",
        **over,
    }


@pytest.mark.parametrize(
    "over",
    [
        {"resource_type": "team"},  # R1
        {"resource_id": str(uuid4())},  # R2
        {"resource_type": "team", "resource_id": "not-a-uuid"},  # R3
        {"entity_type": "panel"},  # R10
        {"resource_id": "all"},  # R11
        {"surprise": 1},
    ],
)
def test_invalid_user_permission_create_is_422(client: TestClient, over: dict[str, Any]) -> None:
    assert client.post("/v1/user-permissions", json=grant(**over), headers=H).status_code == 422


def test_invalid_user_permission_patch_is_422(client: TestClient) -> None:  # P5 for grants
    res = client.patch(f"/v1/user-permissions/{uuid4()}", json={"resource_id": "ALL"}, headers=H)
    assert res.status_code == 422
