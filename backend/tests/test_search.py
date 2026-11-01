import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.deps import get_chunk_search_repo
from app.retrieval.errors import SearchUnavailableError
from app.retrieval.schemas.rag import SearchHit

HIT = SearchHit(chunk_id="c1", document_id="d1", text="hello world", score=1.5)


class FakeSearchRepo:
    def __init__(self, *, is_down: bool = False) -> None:
        self.is_down = is_down

    async def search(self, query: str, top_k: int) -> list[SearchHit]:
        if self.is_down:
            raise SearchUnavailableError("Search is temporarily unavailable")
        return [HIT][:top_k]


def test_search_returns_hits(client: TestClient) -> None:
    app.dependency_overrides[get_chunk_search_repo] = FakeSearchRepo
    res = client.post("/v1/search", json={"query": "hello"})
    assert res.status_code == 200
    assert res.json() == {"hits": [HIT.model_dump()]}


def test_search_store_down_returns_503_envelope(client: TestClient) -> None:
    app.dependency_overrides[get_chunk_search_repo] = lambda: FakeSearchRepo(is_down=True)
    res = client.post("/v1/search", json={"query": "hello"}, headers={"X-Request-ID": "rid-503"})
    assert res.status_code == 503
    assert res.json()["error"] == {
        "code": "search_unavailable",
        "message": "Search is temporarily unavailable",
        "request_id": "rid-503",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},  # empty query
        {"query": "q", "top_k": 0},  # top_k below range
        {"query": "q", "top_k": 51},  # top_k above range
    ],
)
def test_search_invalid_payload_is_422(client: TestClient, payload: dict[str, object]) -> None:
    app.dependency_overrides[get_chunk_search_repo] = FakeSearchRepo
    assert client.post("/v1/search", json=payload).status_code == 422
