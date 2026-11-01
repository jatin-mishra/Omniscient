"""HTTP layer only: validation, status codes, error envelope. Services are stubbed."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.errors import NotFoundError
from app.main import app
from app.onboarding.deps import (
    get_group_service,
    get_group_user_service,
    get_team_service,
    get_user_service,
)
from app.onboarding.models import Status
from app.onboarding.schemas.team import TeamResponse

NOW = datetime.now(UTC)
TEAM = TeamResponse(
    id=uuid4(), name="core", manager_id=None, status=Status.ACTIVE, created_at=NOW, updated_at=NOW
)


class StubTeamService:
    async def create(self, _: Any) -> TeamResponse:
        return TEAM

    async def get(self, team_id: UUID) -> TeamResponse:
        raise NotFoundError(f"Team {team_id} not found")


class NeverCalled:
    """Validation must reject the request before any service method runs."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"service.{name} called for an invalid request")


@pytest.fixture(autouse=True)
def stub_services() -> None:
    for dep in (get_team_service, get_user_service, get_group_service, get_group_user_service):
        app.dependency_overrides[dep] = NeverCalled


def test_create_returns_201_with_uuid_id(client: TestClient) -> None:  # HP-1, HP-5
    app.dependency_overrides[get_team_service] = StubTeamService
    res = client.post("/v1/teams", json={"name": "core"})
    assert res.status_code == 201
    assert res.json()["id"] == str(TEAM.id)
    assert "external_id" not in res.json()


def test_unknown_id_is_404_envelope(client: TestClient) -> None:  # case 1
    app.dependency_overrides[get_team_service] = StubTeamService
    team_id = uuid4()
    res = client.get(f"/v1/teams/{team_id}", headers={"X-Request-ID": "rid-404"})
    assert res.status_code == 404
    assert res.json()["error"] == {
        "code": "not_found",
        "message": f"Team {team_id} not found",
        "request_id": "rid-404",
    }


TEAM_ID = str(uuid4())


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/v1/teams/not-a-uuid", None),  # case 2: malformed uuid in path
        ("post", "/v1/teams", {"name": "  "}),  # case 2: blank name
        ("post", "/v1/teams", {}),  # case 2: missing name
        ("post", "/v1/users", {"name": "A", "email": "nope", "team_id": TEAM_ID}),  # case 2
        ("patch", f"/v1/teams/{TEAM_ID}", {"status": "PAUSED"}),  # case 2: unknown status
        ("patch", f"/v1/teams/{TEAM_ID}", {"name": None}),  # case 2: null on required field
        ("patch", f"/v1/users/{TEAM_ID}", {"team_id": None}),  # case 2
        ("patch", f"/v1/group-users/{TEAM_ID}", {"status": None}),  # case 2
        ("post", "/v1/groups", {"name": "g", "nmae": "typo"}),  # case 3: unknown field
        ("patch", f"/v1/users/{TEAM_ID}", {"email": "new@x.io"}),  # case 11: email immutable
    ],
)
def test_invalid_requests_are_422(
    client: TestClient, method: str, path: str, payload: dict[str, object] | None
) -> None:
    res = client.request(method, path, json=payload)
    assert res.status_code == 422
