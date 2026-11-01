from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.constants.status import Status
from app.retrieval.models import ChunkState, StateStatus
from app.retrieval.schemas.common import Label128, StrictModel


class ChunkCreate(StrictModel):
    state: ChunkState
    state_status: StateStatus
    content: str
    content_summary: str | None = None
    document_summary: str | None = None
    content_checksum: Label128
    metadata: dict[str, Any] = {}

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ChunkUpdate(StrictModel):
    status: Status  # the only setter on Chunk, so it is required (and null is rejected)


class ChunkResponse(BaseModel):
    id: str
    document_id: UUID
    status: Status
    state: ChunkState
    state_status: StateStatus
    content: str
    content_summary: str | None
    document_summary: str | None
    content_checksum: str
    metadata: dict[str, Any]
    changes: list[dict[str, Any]]
    version: int
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_source(cls, source: dict[str, Any]) -> Self:
        return cls(id=source["chunk_id"], **{k: v for k, v in source.items() if k != "chunk_id"})
