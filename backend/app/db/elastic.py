from typing import Any

from elasticsearch import AsyncElasticsearch

from app.core.config import Settings

CHUNKS_MAPPING: dict[str, Any] = {
    "properties": {
        "document_id": {"type": "keyword"},
        "text": {"type": "text"},
    }
}


def create_es_client(settings: Settings) -> AsyncElasticsearch:
    """Build the client. No connection is opened until the first request."""
    return AsyncElasticsearch(settings.elasticsearch_url)


async def ensure_chunk_index(es: AsyncElasticsearch, index: str) -> None:
    if await es.indices.exists(index=index):
        return
    await es.indices.create(index=index, mappings=CHUNKS_MAPPING)
