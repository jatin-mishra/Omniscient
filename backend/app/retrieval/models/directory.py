from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.status import Status, status_column
from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin


class Directory(IdMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "directories"

    name: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("directories.id"))  # null = root
    status: Mapped[Status] = status_column()

    def set_name(self, name: str, actor: UUID) -> None:
        self.name = name
        self.updated_by = actor

    def set_parent_id(self, parent_id: int | None, actor: UUID) -> None:
        self.parent_id = parent_id
        self.updated_by = actor

    def set_status(self, status: Status, actor: UUID) -> None:
        self.status = status
        self.updated_by = actor


# coalesce: Postgres treats NULLs as distinct, so root directories would otherwise bypass this
Index(
    "uq_directories_parent_name",
    func.coalesce(Directory.parent_id, 0),
    func.lower(Directory.name),
    unique=True,
)
