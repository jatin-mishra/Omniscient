from typing import Self
from uuid import UUID

from pydantic import Field, field_validator

from app.constants.status import Status
from app.retrieval.models import Document, Provider, UploadStatus
from app.retrieval.schemas.common import (
    AuditedResponse,
    Bucket,
    DocumentName,
    Label32,
    Label64,
    Label128,
    StoragePath,
    StorageUrl,
    StrictModel,
    reject_null,
)


class DocumentCreate(StrictModel):
    """Metadata only: upload_status starts INITIATED and etag / raw_storage_url are set later."""

    name: DocumentName
    document_type: Label64
    file_type: Label32
    content_type: Label128
    size_in_bytes: int = Field(ge=0)
    directory_id: UUID
    chunking_strategy: Label64
    embedding_model: Label128
    provider: Provider
    bucket: Bucket
    storage_path: StoragePath


class DocumentUpdate(StrictModel):
    """Only the fields that have a setter on Document."""

    name: DocumentName | None = None
    directory_id: UUID | None = None
    etag: Label128 | None = None
    raw_storage_url: StorageUrl | None = None
    upload_status: UploadStatus | None = None
    status: Status | None = None

    _not_null = field_validator(
        "name", "directory_id", "etag", "raw_storage_url", "upload_status", "status"
    )(reject_null)


class DocumentResponse(AuditedResponse):
    name: str
    document_type: str
    file_type: str
    content_type: str
    size_in_bytes: int
    directory_id: UUID
    chunking_strategy: str
    embedding_model: str
    provider: Provider
    bucket: str
    storage_path: str
    raw_storage_url: str | None
    etag: str | None
    upload_status: UploadStatus
    version: int

    @classmethod
    def from_model(cls, document: Document, directory_id: UUID) -> Self:
        return cls(
            id=document.external_id,
            name=document.name,
            document_type=document.document_type,
            file_type=document.file_type,
            content_type=document.content_type,
            size_in_bytes=document.size_in_bytes,
            directory_id=directory_id,
            chunking_strategy=document.chunking_strategy,
            embedding_model=document.embedding_model,
            provider=document.provider,
            bucket=document.bucket,
            storage_path=document.storage_path,
            raw_storage_url=document.raw_storage_url,
            etag=document.etag,
            upload_status=document.upload_status,
            status=document.status,
            version=document.version,
            created_at=document.created_at,
            created_by=document.created_by,
            updated_at=document.updated_at,
            updated_by=document.updated_by,
        )
