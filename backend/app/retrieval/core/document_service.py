from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.status import Status
from app.db.helpers import require
from app.errors import ConflictError
from app.retrieval.models import Directory, Document, UploadStatus
from app.retrieval.repositories.directory_repository import DirectoryRepository
from app.retrieval.repositories.document_repository import DocumentRepository
from app.retrieval.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentRepository,
        directories: DirectoryRepository,
    ) -> None:
        self._session = session
        self._documents = documents
        self._directories = directories

    async def create(self, data: DocumentCreate, actor: UUID) -> DocumentResponse:
        """Records the document's metadata. No bytes are stored yet: the storage providers
        (core/storage.py) are empty, so the document stays INITIATED until a later update."""
        directory = await self._active_directory(data.directory_id)
        document = Document(
            name=data.name,
            document_type=data.document_type,
            file_type=data.file_type,
            content_type=data.content_type,
            size_in_bytes=data.size_in_bytes,
            directory_id=directory.id,
            chunking_strategy=data.chunking_strategy,
            embedding_model=data.embedding_model,
            provider=data.provider,
            bucket=data.bucket,
            storage_path=data.storage_path,
            upload_status=UploadStatus.INITIATED,
            status=Status.ACTIVE,
            version=1,
            created_by=actor,
            updated_by=actor,
        )
        self._documents.add(document)
        await self._session.commit()
        return DocumentResponse.from_model(document, data.directory_id)

    async def update(
        self, document_id: UUID, data: DocumentUpdate, actor: UUID
    ) -> DocumentResponse:
        document = require(
            await self._documents.get_by_external_id(document_id), "Document", document_id
        )
        directory = await self._directories.get(document.directory_id)

        if data.directory_id is not None:
            directory = await self._active_directory(data.directory_id)
            document.set_directory(directory.id, actor)
        if data.name is not None:
            document.set_name(data.name, actor)
        if data.etag is not None:
            document.set_etag(data.etag, actor)
        if data.raw_storage_url is not None:
            document.set_storage_url(data.raw_storage_url, actor)
        if data.upload_status is not None:
            document.set_upload_status(data.upload_status, actor)
        if data.status is not None:
            document.set_status(data.status, actor)

        if data.model_fields_set:
            document.bump_version()
            await self._session.commit()
        return DocumentResponse.from_model(document, directory.external_id)

    async def _active_directory(self, directory_id: UUID) -> Directory:
        directory = require(
            await self._directories.get_by_external_id(directory_id), "Directory", directory_id
        )
        if directory.status is not Status.ACTIVE:
            raise ConflictError(f"Directory {directory_id} is inactive")
        return directory
