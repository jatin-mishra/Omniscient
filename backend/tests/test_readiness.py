import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.deps import get_es
from app.db import postgres
from app.main import app


class FakeEs:
    def __init__(self, is_up: bool) -> None:
        self.is_up = is_up

    async def ping(self) -> bool:
        return self.is_up


@pytest.mark.parametrize(
    ("is_pg_up", "is_es_up", "expected_code", "expected_status"),
    [
        (True, True, 200, "ready"),
        (False, True, 503, "not_ready"),  # postgres down
        (True, False, 503, "not_ready"),  # elasticsearch down
        (False, False, 503, "not_ready"),  # both down
    ],
)
def test_readiness(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    is_pg_up: bool,
    is_es_up: bool,
    expected_code: int,
    expected_status: str,
) -> None:
    async def fake_ping_postgres(_: AsyncEngine) -> bool:
        return is_pg_up

    monkeypatch.setattr(postgres, "ping_postgres", fake_ping_postgres)
    app.dependency_overrides[get_es] = lambda: FakeEs(is_es_up)

    res = client.get("/health/ready")

    assert res.status_code == expected_code
    assert res.json() == {
        "status": expected_status,
        "checks": {"postgres": is_pg_up, "elasticsearch": is_es_up},
    }


def test_liveness_does_not_touch_stores(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exploding_ping(_: AsyncEngine) -> bool:
        raise AssertionError("/health must not ping postgres")

    monkeypatch.setattr(postgres, "ping_postgres", exploding_ping)
    assert client.get("/health").status_code == 200
