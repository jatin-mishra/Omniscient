import asyncio
import logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.elastic import create_es_client, ensure_chunk_index
from app.db.postgres import create_db, create_tables

log = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine, _ = create_db(settings)
    es = create_es_client(settings)
    try:
        await create_tables(engine)
        await ensure_chunk_index(es, settings.es_chunks_index)
        log.info("storage ready: table documents, index %s", settings.es_chunks_index)
    finally:
        await es.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
