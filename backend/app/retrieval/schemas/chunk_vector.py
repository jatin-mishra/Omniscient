from typing import Annotated, Self
from uuid import UUID

from pydantic import StringConstraints

from app.retrieval.models import ChunkVector
from app.retrieval.schemas.common import AuditedResponse, Label64, StrictModel

VectorContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChunkVectorCreate(StrictModel):
    chunk_id: Label64
    document_id: UUID
    content: VectorContent  # text to embed; the vector itself is never accepted from clients


class ChunkVectorResponse(AuditedResponse):
    chunk_id: str
    document_id: UUID

    @classmethod
    def from_model(cls, vector: ChunkVector) -> Self:
        return cls(
            id=vector.external_id,
            chunk_id=vector.chunk_id,
            document_id=vector.document_id,
            status=vector.status,
            created_at=vector.created_at,
            created_by=vector.created_by,
            updated_at=vector.updated_at,
            updated_by=vector.updated_by,
        )
