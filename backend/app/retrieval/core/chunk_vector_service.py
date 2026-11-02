from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.status import Status
from app.db.helpers import commit_or_conflict, require
from app.errors import ConflictError
from app.retrieval.core.embedding import EmbeddingProvider
from app.retrieval.errors import EmbeddingFailedError
from app.retrieval.models import ChunkVector
from app.retrieval.repositories.chunk_vector_repository import ChunkVectorRepository
from app.retrieval.repositories.document_repository import DocumentRepository
from app.retrieval.schemas.chunk_vector import ChunkVectorCreate, ChunkVectorResponse


class ChunkVectorService:
    def __init__(
        self,
        session: AsyncSession,
        vectors: ChunkVectorRepository,
        documents: DocumentRepository,
        embeddings: EmbeddingProvider,
        dimensions: int,
    ) -> None:
        self._session = session
        self._vectors = vectors
        self._documents = documents
        self._embeddings = embeddings
        self._dimensions = dimensions

    async def add(self, data: ChunkVectorCreate, actor: UUID) -> ChunkVectorResponse:
        document = require(
            await self._documents.get_by_external_id(data.document_id),
            "Document",
            data.document_id,
        )
        if document.status is not Status.ACTIVE:
            raise ConflictError(f"Document {data.document_id} is inactive")

        vector = await self._embeddings.embed(data.content)
        if len(vector) != self._dimensions:
            raise EmbeddingFailedError(
                f"Embedding has {len(vector)} dimensions, expected {self._dimensions}"
            )

        chunk_vector = ChunkVector(
            chunk_id=data.chunk_id,
            document_id=data.document_id,
            content=vector,
            status=Status.ACTIVE,
            created_by=actor,
            updated_by=actor,
        )
        self._vectors.add(chunk_vector)
        await commit_or_conflict(
            self._session, f"A vector for chunk '{data.chunk_id}' already exists"
        )
        return ChunkVectorResponse.from_model(chunk_vector)
