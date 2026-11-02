from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.onboarding.models.status import Status, status_column


class GroupUser(IdMixin, TimestampMixin, Base):
    __tablename__ = "group_users"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_users_group_user"),)

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[Status] = status_column()
