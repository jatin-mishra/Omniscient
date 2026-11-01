from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.constants.status import Status
from app.db.helpers import require
from app.errors import ConflictError, NotFoundError
from app.retrieval.models import Document
from app.retrieval.repositories.chunk_repository import ChunkRepository
from app.retrieval.repositories.document_repository import DocumentRepository
from app.retrieval.schemas.chunk import ChunkCreate, ChunkResponse, ChunkUpdate


class ChunkService:
    def __init__(self, chunks: ChunkRepository, documents: DocumentRepository) -> None:
        self._chunks = chunks
        self._documents = documents

    async def add(self, document_id: UUID, data: ChunkCreate, actor: UUID) -> ChunkResponse:
        document = await self._document(document_id)
        if document.status is not Status.ACTIVE:
            raise ConflictError(f"Document {document_id} is inactive")
        chunk_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        source = {
            "chunk_id": chunk_id,
            "document_id": str(document_id),
            "status": Status.ACTIVE.value,
            **data.model_dump(mode="json"),
            "changes": [],  # reserved: update is a plain overwrite for now
            "version": 1,
            "created_at": now,
            "created_by": str(actor),
            "updated_at": now,
            "updated_by": str(actor),
        }
        await self._chunks.add(chunk_id, source)
        return ChunkResponse.from_source(source)

    async def update(
        self, document_id: UUID, chunk_id: str, data: ChunkUpdate, actor: UUID
    ) -> ChunkResponse:
        await self._document(document_id)
        current = await self._chunks.get(chunk_id)
        if current is None or current.source["document_id"] != str(document_id):
            raise NotFoundError(f"Chunk {chunk_id} not found")
        fields = {
            "status": data.status.value,
            "version": current.source["version"] + 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "updated_by": str(actor),
        }
        await self._chunks.update(chunk_id, current, fields)
        return ChunkResponse.from_source({**current.source, **fields})

    async def _document(self, document_id: UUID) -> Document:
        found = await self._documents.get_by_external_id(document_id)
        return require(found, "Document", document_id)
