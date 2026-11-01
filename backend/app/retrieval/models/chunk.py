from typing import Any

from elasticsearch import AsyncElasticsearch

CHUNKS_MAPPING: dict[str, Any] = {
    "properties": {
        "document_id": {"type": "keyword"},
        "text": {"type": "text"},
    }
}


async def ensure_chunk_index(es: AsyncElasticsearch, index: str) -> None:
    if await es.indices.exists(index=index):
        return
    await es.indices.create(index=index, mappings=CHUNKS_MAPPING)
