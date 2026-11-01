from elasticsearch import AsyncElasticsearch

from app.config import Settings


def create_es_client(settings: Settings) -> AsyncElasticsearch:
    """Build the client. No connection is opened until the first request."""
    return AsyncElasticsearch(settings.elasticsearch_url)
