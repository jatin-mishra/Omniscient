"""retrieval against real Postgres + Elasticsearch (ids refer to metric/test_cases_and_metrics.yml).
Rows are committed and left behind, so every name is unique per run."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.integration

H = {"X-User-Id": str(uuid4())}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CREATE_SCHEMA_ON_STARTUP", "true")  # I1, I4: schema + index at startup
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def make_dir(api: TestClient, name: str | None = None, parent: str | None = None) -> dict[str, Any]:
    res = api.post(
        "/v1/directories", json={"name": name or uniq("d"), "parent_id": parent}, headers=H
    )
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


def doc_body(directory_id: str) -> dict[str, Any]:
    return {
        "name": "a.pdf",
        "document_type": "policy",
        "file_type": "pdf",
        "content_type": "application/pdf",
        "size_in_bytes": 10,
        "directory_id": directory_id,
        "chunking_strategy": "structure_aware",
        "embedding_model": "m",
        "provider": "aws",
        "bucket": "b",
        "storage_path": "p",
    }


def test_end_to_end(api: TestClient) -> None:  # I2, I4
    root = make_dir(api)
    child = make_dir(api, parent=root["id"])
    assert child["parent_id"] == root["id"] and "external_id" not in child

    created = api.post("/v1/documents", json=doc_body(child["id"]), headers=H)
    assert created.status_code == 201
    doc = created.json()
    assert (doc["upload_status"], doc["version"]) == ("INITIATED", 1)

    patched = api.patch(
        f"/v1/documents/{doc['id']}",
        json={"etag": "e1", "raw_storage_url": "s3://b/p", "upload_status": "SUCCESS"},
        headers=H,
    )
    assert patched.status_code == 200
    assert (patched.json()["version"], patched.json()["etag"]) == (2, "e1")

    body = {
        "state": "chunking",
        "state_status": "success",
        "content": "hello world",
        "content_checksum": "abc",
        "metadata": {"page": 1},
    }
    chunk = api.post(f"/v1/documents/{doc['id']}/chunks", json=body, headers=H)
    assert chunk.status_code == 201, chunk.text
    chunk_id = chunk.json()["id"]
    assert chunk.json()["changes"] == [] and chunk.json()["version"] == 1

    updated = api.patch(
        f"/v1/documents/{doc['id']}/chunks/{chunk_id}", json={"status": "INACTIVE"}, headers=H
    )
    assert updated.status_code == 200
    assert (updated.json()["status"], updated.json()["version"]) == ("INACTIVE", 2)
    assert updated.json()["metadata"] == {"page": 1}

    other = api.post("/v1/documents", json=doc_body(root["id"]), headers=H).json()
    wrong_doc = api.patch(
        f"/v1/documents/{other['id']}/chunks/{chunk_id}", json={"status": "ACTIVE"}, headers=H
    )
    assert wrong_doc.status_code == 404  # C6


def test_directory_constraints_in_postgres(api: TestClient) -> None:  # I1, D2, D3, D4, D6
    name = uniq("dup")
    first = make_dir(api, name)
    assert api.post("/v1/directories", json={"name": name.upper()}, headers=H).status_code == 409
    parent = make_dir(api)
    make_dir(api, name, parent["id"])  # same name, different parent
    cycle = api.patch(f"/v1/directories/{parent['id']}", json={"parent_id": first["id"]}, headers=H)
    assert cycle.status_code == 200
    loop = api.patch(f"/v1/directories/{first['id']}", json={"parent_id": parent["id"]}, headers=H)
    assert loop.status_code == 422


def test_concurrent_duplicate_directory(api: TestClient) -> None:  # I3
    name = uniq("race")

    def post() -> int:
        return api.post("/v1/directories", json={"name": name}, headers=H).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(lambda _: post(), range(2)))
    assert codes == [201, 409]
