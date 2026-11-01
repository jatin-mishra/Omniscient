from typing import Any

from elasticsearch import AsyncElasticsearch

CHUNKS_MAPPING: dict[str, Any] = {
    "dynamic": "strict",
    "properties": {
        "chunk_id": {"type": "keyword"},
        "document_id": {"type": "keyword"},
        "status": {"type": "keyword"},
        "state": {"type": "keyword"},
        "state_status": {"type": "keyword"},
        "content": {"type": "text"},
        "content_summary": {"type": "text"},
        "document_summary": {"type": "text"},
        "content_checksum": {"type": "keyword"},
        "metadata": {"type": "object", "dynamic": False},
        "changes": {"type": "object", "dynamic": False},
        "version": {"type": "integer"},
        "created_at": {"type": "date"},
        "created_by": {"type": "keyword"},
        "updated_at": {"type": "date"},
        "updated_by": {"type": "keyword"},
    },
}


async def ensure_chunk_index(es: AsyncElasticsearch, index: str) -> None:
    """Creates the index if missing. Never alters an existing one: delete the old index first."""
    if await es.indices.exists(index=index):
        return
    await es.indices.create(index=index, mappings=CHUNKS_MAPPING)
