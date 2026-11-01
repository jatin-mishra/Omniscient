from typing import Self
from uuid import UUID

from pydantic import field_validator

from app.constants.status import Status
from app.retrieval.models import Directory
from app.retrieval.schemas.common import AuditedResponse, Name, StrictModel, reject_null


class DirectoryCreate(StrictModel):
    name: Name
    parent_id: UUID | None = None  # null = root


class DirectoryUpdate(StrictModel):
    name: Name | None = None
    parent_id: UUID | None = None  # null moves the directory to the root
    status: Status | None = None

    _not_null = field_validator("name", "status")(reject_null)


class DirectoryResponse(AuditedResponse):
    name: str
    parent_id: UUID | None

    @classmethod
    def from_model(cls, directory: Directory, parent_id: UUID | None) -> Self:
        return cls(
            id=directory.external_id,
            name=directory.name,
            parent_id=parent_id,
            status=directory.status,
            created_at=directory.created_at,
            created_by=directory.created_by,
            updated_at=directory.updated_at,
            updated_by=directory.updated_by,
        )
