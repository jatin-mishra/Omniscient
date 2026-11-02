from uuid import UUID

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.status import Status, status_column
from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin
from app.retrieval.models.enums import Provider, UploadStatus


class Document(IdMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(64))
    file_type: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str] = mapped_column(String(128))
    size_in_bytes: Mapped[int] = mapped_column(BigInteger)

    directory_id: Mapped[int] = mapped_column(ForeignKey("directories.id"))
    chunking_strategy: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(128))

    provider: Mapped[Provider] = mapped_column(
        Enum(
            Provider,
            native_enum=False,
            create_constraint=True,
            length=8,
            values_callable=lambda e: [m.value for m in e],
        )
    )
    bucket: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(1024))
    raw_storage_url: Mapped[str | None] = mapped_column(String(2048))
    etag: Mapped[str | None] = mapped_column(String(128))

    upload_status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, native_enum=False, create_constraint=True, length=16),
        default=UploadStatus.INITIATED,
    )
    status: Mapped[Status] = status_column()
    version: Mapped[int] = mapped_column(default=1)

    def set_name(self, name: str, actor: UUID) -> None:
        self.name = name
        self.updated_by = actor

    def set_directory(self, directory_id: int, actor: UUID) -> None:
        self.directory_id = directory_id
        self.updated_by = actor

    def set_etag(self, etag: str, actor: UUID) -> None:
        self.etag = etag
        self.updated_by = actor

    def set_storage_url(self, url: str, actor: UUID) -> None:
        self.raw_storage_url = url
        self.updated_by = actor

    def set_upload_status(self, upload_status: UploadStatus, actor: UUID) -> None:
        self.upload_status = upload_status
        self.updated_by = actor

    def set_status(self, status: Status, actor: UUID) -> None:
        self.status = status
        self.updated_by = actor

    def bump_version(self) -> None:
        self.version += 1
