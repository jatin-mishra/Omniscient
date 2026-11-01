from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.onboarding.models.status import Status, status_column


class Group(IdMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[Status] = status_column()


Index("uq_groups_name_lower", func.lower(Group.name), unique=True)
