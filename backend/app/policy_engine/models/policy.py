from uuid import UUID

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.status import Status, status_column
from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin
from app.policy_engine.models.effect import Effect


class Policy(IdMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("permission_name", "effect", name="uq_policies_perm_effect"),
    )

    # Permission is an enum in code, a plain string here (validated at the API boundary)
    permission_name: Mapped[str] = mapped_column(String(64))
    effect: Mapped[Effect] = mapped_column(
        Enum(Effect, native_enum=False, create_constraint=True, length=8)
    )
    status: Mapped[Status] = status_column()

    def set_status(self, status: Status, actor: UUID) -> None:
        self.status = status
        self.updated_by = actor
