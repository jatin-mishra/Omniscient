from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import SearchUnavailableError
from app.db.elastic import create_es_client, ensure_chunk_index
from app.db.postgres import create_db, create_tables
from app.repositories.chunk_search_repository import ChunkSearchRepository
from app.repositories.document_repository import DocumentRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine, sessionmaker = create_db(get_settings())
    await create_tables(engine)
    async with sessionmaker() as s:
        yield s  # never committed: rolled back on close, so tests leave no rows
    await engine.dispose()


@pytest.fixture
async def es() -> AsyncIterator[AsyncElasticsearch]:
    client = create_es_client(get_settings())
    yield client
    await client.close()


@pytest.fixture
async def chunk_index(es: AsyncElasticsearch) -> AsyncIterator[str]:
    index = f"chunks-test-{uuid4().hex}"  # throwaway index, never touches real data
    await ensure_chunk_index(es, index)
    yield index
    await es.indices.delete(index=index)


@pytest.mark.anyio
async def test_document_round_trip(session: AsyncSession) -> None:
    repo = DocumentRepository(session)
    created = await repo.add(source="notes.txt", text="hello")
    fetched = await repo.get(created.id)
    assert fetched is not None
    assert (fetched.source, fetched.text) == ("notes.txt", "hello")
    assert fetched.created_at is not None  # filled by postgres server_default


@pytest.mark.anyio
async def test_get_unknown_document_returns_none(session: AsyncSession) -> None:
    assert await DocumentRepository(session).get(uuid4()) is None


@pytest.mark.anyio
async def test_indexed_chunk_is_searchable(es: AsyncElasticsearch, chunk_index: str) -> None:
    repo = ChunkSearchRepository(es, chunk_index)
    await repo.index_chunk("c1", "d1", "postgres and elasticsearch integration")
    await es.indices.refresh(index=chunk_index)  # make it searchable now, not in ~1s
    hits = await repo.search("elasticsearch", top_k=5)
    assert [(h.chunk_id, h.document_id) for h in hits] == [("c1", "d1")]


@pytest.mark.anyio
async def test_search_on_missing_index_raises(es: AsyncElasticsearch) -> None:
    repo = ChunkSearchRepository(es, f"missing-{uuid4().hex}")
    with pytest.raises(SearchUnavailableError):
        await repo.search("anything", top_k=5)


def test_readiness_against_real_stores(client: TestClient) -> None:
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["checks"] == {"postgres": True, "elasticsearch": True}
