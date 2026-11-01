from typing import Any
from uuid import UUID

from app.constants.status import Status
from app.retrieval.core.chunk_service import ChunkService
from app.retrieval.core.directory_service import DirectoryService
from app.retrieval.core.document_service import DocumentService
from app.retrieval.models import Directory, Document
from app.retrieval.repositories.chunk_repository import StoredChunk
from tests.onboarding.fakes import FakeRepo, FakeSession


class FakeChunks:
    """In-memory ES: keyed by chunk_id, with a seq_no bumped on every write."""

    def __init__(self) -> None:
        self.docs: dict[str, StoredChunk] = {}

    async def add(self, chunk_id: str, source: dict[str, Any]) -> None:
        self.docs[chunk_id] = StoredChunk(source, 1, 1)

    async def get(self, chunk_id: str) -> StoredChunk | None:
        return self.docs.get(chunk_id)

    async def update(self, chunk_id: str, current: StoredChunk, fields: dict[str, Any]) -> None:
        self.docs[chunk_id] = StoredChunk({**current.source, **fields}, current.seq_no + 1, 1)


class FakeDb:
    def __init__(self) -> None:
        session = FakeSession()
        self.directories_repo = FakeRepo[Directory]()
        self.documents_repo = FakeRepo[Document]()
        self.chunks_repo = FakeChunks()
        self.directories = DirectoryService(session, self.directories_repo)  # type: ignore[arg-type]
        self.documents = DocumentService(
            session,  # type: ignore[arg-type]
            self.documents_repo,  # type: ignore[arg-type]
            self.directories_repo,  # type: ignore[arg-type]
        )
        self.chunks = ChunkService(self.chunks_repo, self.documents_repo)  # type: ignore[arg-type]

    def deactivate_directory(self, external_id: UUID) -> None:
        next(
            d for d in self.directories_repo.rows if d.external_id == external_id
        ).status = Status.INACTIVE

    def deactivate_document(self, external_id: UUID) -> None:
        next(
            d for d in self.documents_repo.rows if d.external_id == external_id
        ).status = Status.INACTIVE
