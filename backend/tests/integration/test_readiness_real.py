import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_readiness_against_real_stores(client: TestClient) -> None:
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["checks"] == {"postgres": True, "elasticsearch": True}
