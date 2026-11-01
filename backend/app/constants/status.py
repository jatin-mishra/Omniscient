from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column


class Status(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


def status_column() -> Mapped[Status]:
    # VARCHAR + CHECK instead of a native PG enum: adding a value later needs no ALTER TYPE
    return mapped_column(
        Enum(Status, native_enum=False, create_constraint=True, length=16),
        default=Status.ACTIVE,
    )
