from uuid import UUID

from sqlalchemy import BigInteger, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.permissions import ResourceType
from app.constants.status import Status, status_column
from app.db.base import AuditMixin, Base, IdMixin, TimestampMixin
from app.policy_engine.models.entity_type import EntityType

# Store the lowercase values (team), not member names (TEAM), so rows match the API
_ENUM_KW = {
    "native_enum": False,
    "create_constraint": True,
    "length": 16,
    "values_callable": lambda e: [m.value for m in e],
}


class UserPermission(IdMixin, TimestampMixin, AuditMixin, Base):
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "policy_id",
            "resource_type",
            "resource_id",
            name="uq_user_permissions_grant",
        ),
    )

    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, **_ENUM_KW))
    # Owned by another module, so a plain UUID with no FK
    entity_id: Mapped[UUID] = mapped_column()
    policy_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("policies.id"))
    resource_type: Mapped[ResourceType] = mapped_column(Enum(ResourceType, **_ENUM_KW))
    resource_id: Mapped[str] = mapped_column(String(36))  # "ALL" or a UUID
    status: Mapped[Status] = status_column()

    def mark_status(self, status: Status, actor: UUID) -> None:
        self.status = status
        self.updated_by = actor
