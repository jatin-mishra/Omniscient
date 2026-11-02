from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.constants.status import Status, status_column
from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin


class ChunkVector(IdMixin, TimestampMixin, AuditMixin, Base):
    """Embedding of one chunk. The dimension is fixed when the table is created (no migrations
    yet), so changing EMBEDDING_DIMENSIONS later means recreating the table."""

    __tablename__ = "chunk_vectors"

    chunk_id: Mapped[str] = mapped_column(String(64), unique=True)  # the ES chunk's id
    document_id: Mapped[UUID] = mapped_column(index=True)  # the document's external id
    content: Mapped[list[float]] = mapped_column(Vector(get_settings().embedding_dimensions))
    status: Mapped[Status] = status_column()

    def set_status(self, status: Status, actor: UUID) -> None:
        self.status = status
        self.updated_by = actor
