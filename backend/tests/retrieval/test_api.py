"""HTTP layer only: validation, auth header, status codes. Services are stubbed or forbidden."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.deps import get_chunk_service, get_directory_service, get_document_service

H = {"X-User-Id": str(uuid4())}
DOC: dict[str, Any] = {
    "name": "a.pdf",
    "document_type": "policy",
    "file_type": "pdf",
    "content_type": "application/pdf",
    "size_in_bytes": 0,
    "directory_id": str(uuid4()),
    "chunking_strategy": "structure_aware",
    "embedding_model": "m",
    "provider": "aws",
    "bucket": "b",
    "storage_path": "p",
}
CHUNK: dict[str, Any] = {
    "state": "chunking",
    "state_status": "in-progress",
    "content": "hello",
    "content_checksum": "abc",
}
DOC_ID, CHUNK_ID = uuid4(), "c1"


class NeverCalled:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"service.{name} called for an invalid request")


class Echo:
    """Accepts any call: proves a request got past validation."""

    def __getattr__(self, name: str) -> Any:
        async def call(*_: Any) -> dict[str, Any]:
            raise RuntimeError("reached the service")

        return call


@pytest.fixture(autouse=True)
def forbid_services() -> None:
    for dep in (get_directory_service, get_document_service, get_chunk_service):
        app.dependency_overrides[dep] = NeverCalled


def test_old_retrieval_apis_removed(client: TestClient) -> None:  # X1
    assert client.post("/v1/query", json={"question": "q"}, headers=H).status_code == 404
    assert client.post("/v1/search", json={"query": "q"}, headers=H).status_code == 404
    old = {"source": "notes.txt", "text": "hello"}
    assert client.post("/v1/documents", json=old, headers=H).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/v1/directories", {"name": "x"}),
        ("patch", f"/v1/directories/{uuid4()}", {"name": "x"}),
        ("post", "/v1/documents", DOC),
        ("patch", f"/v1/documents/{uuid4()}", {"name": "x"}),
        ("post", f"/v1/documents/{DOC_ID}/chunks", CHUNK),
        ("patch", f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", {"status": "INACTIVE"}),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "not-a-uuid"}])
def test_auth_header_required(
    client: TestClient, method: str, path: str, body: dict[str, Any], headers: dict[str, str]
) -> None:  # A1
    assert getattr(client, method)(path, json=body, headers=headers).status_code == 401


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/directories", {"name": ""}),  # D10
        ("/v1/directories", {"name": "   "}),
        ("/v1/directories", {"name": "x" * 129}),
        ("/v1/directories", {"name": "x", "created_by": str(uuid4())}),  # D11
        ("/v1/directories", {"name": "x", "status": "INACTIVE"}),
        ("/v1/documents", {**DOC, "provider": "azure"}),  # DO3
        ("/v1/documents", {**DOC, "size_in_bytes": -1}),  # DO4
        ("/v1/documents", {**DOC, "name": " "}),  # DO5
        ("/v1/documents", {**DOC, "bucket": ""}),
        ("/v1/documents", {**DOC, "upload_status": "SUCCESS"}),  # DO6
        ("/v1/documents", {**DOC, "version": 5}),
        ("/v1/documents", {**DOC, "etag": "e"}),
        ("/v1/documents", {**DOC, "status": "INACTIVE"}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "state": "indexing"}),  # C3
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "state_status": "done"}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "content": ""}),  # C4
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "content": "  "}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "content_checksum": " "}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "metadata": "text"}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "chunk_id": "x"}),  # C7
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "version": 3}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "changes": []}),
        (f"/v1/documents/{DOC_ID}/chunks", {**CHUNK, "status": "INACTIVE"}),
    ],
)
def test_create_validation_422(client: TestClient, path: str, body: dict[str, Any]) -> None:
    assert client.post(path, json=body, headers=H).status_code == 422


@pytest.mark.parametrize(
    ("path", "body"),
    [
        (f"/v1/directories/{uuid4()}", {"name": None}),  # D7
        (f"/v1/directories/{uuid4()}", {"status": None}),
        (f"/v1/directories/{uuid4()}", {"name": "x" * 129}),
        (f"/v1/directories/{uuid4()}", {"created_by": str(uuid4())}),
    ]
    + [
        (f"/v1/documents/{uuid4()}", {field: "x"})  # DO7: no setter -> not patchable
        for field in ("version", "provider", "bucket", "storage_path", "size_in_bytes")
    ]
    + [
        (f"/v1/documents/{uuid4()}", {field: None})  # DO9
        for field in ("name", "directory_id", "etag", "raw_storage_url", "upload_status", "status")
    ]
    + [
        (f"/v1/documents/{uuid4()}", {"upload_status": "DONE"}),  # DO3
        (f"/v1/documents/{uuid4()}", {"status": "DELETED"}),
        (f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", {"status": None}),  # C8
        (f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", {}),
        (f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", {"status": "ACTIVE", "content": "x"}),
        (f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", {"state": "embedding"}),
    ],
)
def test_patch_validation_422(client: TestClient, path: str, body: dict[str, Any]) -> None:
    assert client.patch(path, json=body, headers=H).status_code == 422


def test_valid_requests_reach_the_service(client: TestClient) -> None:  # HP-1, HP-4, HP-6
    for dep in (get_directory_service, get_document_service, get_chunk_service):
        app.dependency_overrides[dep] = Echo
    ok = [
        client.post("/v1/directories", json={"name": " x ", "parent_id": None}, headers=H),
        client.patch(f"/v1/directories/{uuid4()}", json={"parent_id": None}, headers=H),
        client.post("/v1/documents", json=DOC, headers=H),
        client.patch(f"/v1/documents/{uuid4()}", json={"etag": "e"}, headers=H),
        client.post(f"/v1/documents/{DOC_ID}/chunks", json=CHUNK, headers=H),
        client.patch(
            f"/v1/documents/{DOC_ID}/chunks/{CHUNK_ID}", json={"status": "INACTIVE"}, headers=H
        ),
    ]
    assert [r.status_code for r in ok] == [500] * 6  # Echo raises past validation
    assert all(r.json()["error"]["code"] == "internal_error" for r in ok)
