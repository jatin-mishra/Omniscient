from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.onboarding.models.status import Status, status_column


class Team(IdMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(128))
    # use_alter: teams <-> users reference each other, so this FK is added after both tables exist
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_teams_manager_id_users")
    )
    status: Mapped[Status] = status_column()


Index("uq_teams_name_lower", func.lower(Team.name), unique=True)
