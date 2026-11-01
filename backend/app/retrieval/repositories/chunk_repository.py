import logging
from dataclasses import dataclass
from typing import Any

from elasticsearch import ApiError, AsyncElasticsearch, TransportError
from elasticsearch import ConflictError as EsConflictError
from elasticsearch import NotFoundError as EsNotFoundError

from app.errors import ConflictError
from app.retrieval.errors import SearchUnavailableError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredChunk:
    source: dict[str, Any]
    seq_no: int  # with primary_term, lets update() detect a concurrent change
    primary_term: int


class ChunkRepository:
    """Chunks in Elasticsearch, keyed by chunk_id. ES failures become SearchUnavailableError."""

    def __init__(self, es: AsyncElasticsearch, index: str) -> None:
        self._es = es
        self._index = index

    async def add(self, chunk_id: str, source: dict[str, Any]) -> None:
        try:
            await self._es.index(index=self._index, id=chunk_id, document=source, op_type="create")
        except (ApiError, TransportError) as exc:
            raise _unavailable(exc) from exc

    async def get(self, chunk_id: str) -> StoredChunk | None:
        try:
            res = await self._es.get(index=self._index, id=chunk_id)
        except EsNotFoundError:
            return None
        except (ApiError, TransportError) as exc:
            raise _unavailable(exc) from exc
        return StoredChunk(res["_source"], res["_seq_no"], res["_primary_term"])

    async def update(self, chunk_id: str, current: StoredChunk, fields: dict[str, Any]) -> None:
        """Partial update guarded by the version read in get(); a lost race is a 409."""
        try:
            await self._es.index(
                index=self._index,
                id=chunk_id,
                document={**current.source, **fields},
                if_seq_no=current.seq_no,
                if_primary_term=current.primary_term,
            )
        except EsConflictError as exc:
            raise ConflictError("Chunk was modified concurrently; retry") from exc
        except (ApiError, TransportError) as exc:
            raise _unavailable(exc) from exc


def _unavailable(exc: Exception) -> SearchUnavailableError:
    log.warning("elasticsearch call failed: %s", exc)
    return SearchUnavailableError("Chunk store is temporarily unavailable")
