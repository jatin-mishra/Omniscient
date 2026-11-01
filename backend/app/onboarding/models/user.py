from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.onboarding.models.status import Status, status_column


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(320))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[Status] = status_column()


Index("uq_users_email_lower", func.lower(User.email), unique=True)
