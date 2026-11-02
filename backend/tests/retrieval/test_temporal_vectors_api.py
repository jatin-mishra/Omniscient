"""HTTP layer for workflows + chunk-vectors (ids refer to metric/test_cases_and_metrics.yml,
Temporal + ChunkVector section)."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.constants.status import Status
from app.main import app
from app.retrieval.deps import get_chunk_vector_service, get_workflow_service
from app.retrieval.schemas.chunk_vector import ChunkVectorResponse
from app.retrieval.schemas.workflow import WorkflowAccepted
from tests.retrieval.test_api import NeverCalled

ACTOR = uuid4()
H = {"X-User-Id": str(ACTOR)}
VECTOR: dict[str, Any] = {"chunk_id": "c1", "document_id": str(uuid4()), "content": "hello"}


class StubWorkflows:
    async def trigger_log(self, message: str) -> WorkflowAccepted:
        return WorkflowAccepted(workflow_id=f"log-{message}")


class StubVectors:
    async def add(self, data: Any, actor: Any) -> ChunkVectorResponse:
        now = datetime.now(UTC)
        return ChunkVectorResponse(
            id=uuid4(),
            chunk_id=data.chunk_id,
            document_id=data.document_id,
            status=Status.ACTIVE,
            created_at=now,
            created_by=actor,
            updated_at=now,
            updated_by=actor,
        )


@pytest.fixture
def forbid() -> None:
    app.dependency_overrides[get_workflow_service] = NeverCalled
    app.dependency_overrides[get_chunk_vector_service] = NeverCalled


def test_trigger_returns_accepted(client: TestClient) -> None:  # W1
    app.dependency_overrides[get_workflow_service] = StubWorkflows
    res = client.post("/v1/workflows/log", json={"message": "hi"}, headers=H)
    assert res.status_code == 202
    assert res.json() == {"workflow_id": "log-hi"}


@pytest.mark.usefixtures("forbid")
@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ({}, {"message": "hi"}),  # W2 missing header
        ({"X-User-Id": "nope"}, {"message": "hi"}),  # W2 non-UUID
    ],
)
def test_trigger_requires_actor(client: TestClient, headers: dict[str, str], body: Any) -> None:
    assert client.post("/v1/workflows/log", json=body, headers=headers).status_code == 401


@pytest.mark.usefixtures("forbid")
@pytest.mark.parametrize(
    "body",
    [
        {"message": ""},  # W3
        {"message": "   "},  # W3
        {"message": "x", "extra": 1},  # W3
        {"message": "x" * 1001},  # W6
        {},  # W3
    ],
)
def test_trigger_validation(client: TestClient, body: Any) -> None:
    assert client.post("/v1/workflows/log", json=body, headers=H).status_code == 422


def test_add_vector_created(client: TestClient) -> None:  # V1
    app.dependency_overrides[get_chunk_vector_service] = StubVectors
    res = client.post("/v1/chunk-vectors", json=VECTOR, headers=H)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ACTIVE"
    assert body["created_by"] == body["updated_by"] == str(ACTOR)
    assert "content" not in body and "vector" not in body  # vector never echoed
    assert isinstance(body["id"], str)  # UUID, not the BIGINT


@pytest.mark.usefixtures("forbid")
def test_add_vector_requires_actor(client: TestClient) -> None:  # V3
    assert client.post("/v1/chunk-vectors", json=VECTOR).status_code == 401
    bad = {"X-User-Id": "nope"}
    assert client.post("/v1/chunk-vectors", json=VECTOR, headers=bad).status_code == 401


@pytest.mark.usefixtures("forbid")
@pytest.mark.parametrize(
    "over",
    [
        {"chunk_id": ""},  # V4
        {"chunk_id": "x" * 65},  # V4
        {"content": "  "},  # V4
        {"document_id": "not-a-uuid"},  # V4
        {"unknown": 1},  # V4
        {"status": "INACTIVE"},  # V5
        {"created_by": str(uuid4())},  # V5
        {"updated_by": str(uuid4())},  # V5
        {"vector": [0.1]},  # V5
    ],
)
def test_add_vector_validation(client: TestClient, over: dict[str, Any]) -> None:
    res = client.post("/v1/chunk-vectors", json={**VECTOR, **over}, headers=H)
    assert res.status_code == 422


@pytest.mark.usefixtures("forbid")
def test_add_vector_missing_fields(client: TestClient) -> None:  # V4
    for field in VECTOR:
        body = {k: v for k, v in VECTOR.items() if k != field}
        assert client.post("/v1/chunk-vectors", json=body, headers=H).status_code == 422
