from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. Values come from the environment, then `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "omniscient"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = []
    database_url: str = "postgresql+asyncpg://omniscient:omniscient@localhost:5432/omniscient"
    elasticsearch_url: str = "http://localhost:9200"
    es_chunks_index: str = "chunks"
    create_schema_on_startup: bool = True  # create missing tables + ES index (idempotent)

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_api_key: str = ""  # empty = no auth (local dev server)
    temporal_tls: bool = False
    temporal_task_queue: str = "retrieval"
    temporal_connect_timeout_s: float = Field(5.0, gt=0)
    temporal_rpc_timeout_s: float = Field(10.0, gt=0)
    workflow_execution_timeout_s: float = Field(300.0, gt=0)

    tracker_webhook_secret: str = ""  # empty = every ticket webhook is rejected (fail closed)

    embedding_provider: str = "constant"
    embedding_dimensions: int = Field(1536, gt=0)  # fixed per vector column; see ChunkVector

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached so settings are parsed once; call `get_settings.cache_clear()` in tests."""
    return Settings()
