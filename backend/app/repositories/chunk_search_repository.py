import logging

from elasticsearch import ApiError, AsyncElasticsearch, TransportError

from app.core.errors import SearchUnavailableError
from app.schemas.rag import SearchHit

log = logging.getLogger(__name__)


class ChunkSearchRepository:
    """Data access for the chunks index. `search` maps ES failures to SearchUnavailableError."""

    def __init__(self, es: AsyncElasticsearch, index: str) -> None:
        self._es = es
        self._index = index

    async def index_chunk(self, chunk_id: str, document_id: str, text: str) -> None:
        await self._es.index(
            index=self._index, id=chunk_id, document={"document_id": document_id, "text": text}
        )

    async def search(self, query: str, top_k: int) -> list[SearchHit]:
        try:
            response = await self._es.search(
                index=self._index, query={"match": {"text": query}}, size=top_k
            )
        except (ApiError, TransportError) as exc:
            log.warning("elasticsearch search failed: %s", exc)
            raise SearchUnavailableError("Search is temporarily unavailable") from exc
        return [
            SearchHit(
                chunk_id=hit["_id"],
                document_id=hit["_source"]["document_id"],
                text=hit["_source"]["text"],
                score=hit["_score"],
            )
            for hit in response["hits"]["hits"]
        ]
