"""Temporal + pgvector against real services (ids: metric file, Temporal + ChunkVector section).
Needs `make infra-up` (pgvector Postgres, Elasticsearch, Temporal dev server)."""

import asyncio
import logging
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.main import app
from app.retrieval.temporal.client import create_temporal_client
from app.retrieval.temporal.worker import build_worker
from tests.integration.test_retrieval import doc_body, make_dir, uniq

pytestmark = pytest.mark.integration

H = {"X-User-Id": str(uuid4())}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CREATE_SCHEMA_ON_STARTUP", "true")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


async def scalar(sql: str, **params: Any) -> str:
    """Own engine: the app's pool is bound to the TestClient's event loop, not this one."""
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            return str((await conn.execute(text(sql), params)).scalar_one())
    finally:
        await engine.dispose()


def make_document(api: TestClient) -> str:
    res = api.post("/v1/documents", json=doc_body(make_dir(api)["id"]), headers=H)
    assert res.status_code == 201, res.text
    document_id: str = res.json()["id"]
    return document_id


def add_vector(api: TestClient, document_id: str, chunk_id: str) -> Any:
    body = {"chunk_id": chunk_id, "document_id": document_id, "content": "hello"}
    return api.post("/v1/chunk-vectors", json=body, headers=H)


def test_extension_and_column(api: TestClient) -> None:  # I1
    sql = (
        "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
        "WHERE attrelid = 'chunk_vectors'::regclass AND attname = 'content'"
    )
    expected = f"vector({get_settings().embedding_dimensions})"
    assert asyncio.run(scalar(sql)) == expected


def test_add_vector_end_to_end(api: TestClient) -> None:  # I2, I3
    document_id, chunk_id = make_document(api), uniq("chunk")
    res = add_vector(api, document_id, chunk_id)
    assert res.status_code == 201, res.text

    values = (
        asyncio.run(
            scalar("SELECT content::text FROM chunk_vectors WHERE chunk_id = :c", c=chunk_id)
        )
        .strip("[]")
        .split(",")
    )
    assert len(values) == get_settings().embedding_dimensions
    assert {float(v) for v in values} == {0.1}  # the stub's constant

    assert add_vector(api, document_id, chunk_id).status_code == 409  # I3 unique chunk_id


def test_unknown_document_is_404(api: TestClient) -> None:  # V6
    assert add_vector(api, str(uuid4()), uniq("chunk")).status_code == 404


def test_trigger_workflow_runs_activity(
    api: TestClient, caplog: pytest.LogCaptureFixture
) -> None:  # I4, K1, K2, K3
    message = uniq("msg")
    settings = get_settings()

    async def scenario() -> None:
        client = await create_temporal_client(settings, lazy=False)
        async with build_worker(client, settings):  # K2/K3: registers + sandbox-validates
            res = await asyncio.to_thread(
                api.post, "/v1/workflows/log", json={"message": message}, headers=H
            )
            assert res.status_code == 202, res.text
            handle = client.get_workflow_handle(res.json()["workflow_id"])
            await asyncio.wait_for(handle.result(), timeout=30)

    caplog.set_level(logging.INFO)
    asyncio.run(scenario())
    assert message in caplog.text
