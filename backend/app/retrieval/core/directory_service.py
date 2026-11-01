from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.status import Status
from app.db.helpers import commit_or_conflict, require
from app.errors import ConflictError, InvalidRequestError
from app.retrieval.models import Directory
from app.retrieval.repositories.directory_repository import DirectoryRepository
from app.retrieval.schemas.directory import DirectoryCreate, DirectoryResponse, DirectoryUpdate

DUPLICATE = "A directory with that name already exists under the parent"


class DirectoryService:
    def __init__(self, session: AsyncSession, directories: DirectoryRepository) -> None:
        self._session = session
        self._directories = directories

    async def create(self, data: DirectoryCreate, actor: UUID) -> DirectoryResponse:
        parent = await self._active_parent(data.parent_id)
        directory = Directory(
            name=data.name,
            parent_id=parent.id if parent else None,
            status=Status.ACTIVE,
            created_by=actor,
            updated_by=actor,
        )
        self._directories.add(directory)
        await commit_or_conflict(self._session, DUPLICATE)
        return DirectoryResponse.from_model(directory, data.parent_id)

    async def update(
        self, directory_id: UUID, data: DirectoryUpdate, actor: UUID
    ) -> DirectoryResponse:
        directory = require(
            await self._directories.get_by_external_id(directory_id), "Directory", directory_id
        )
        parent = await self._parent_of(directory)

        if "parent_id" in data.model_fields_set:  # null is meaningful here: move to the root
            parent = await self._active_parent(data.parent_id)
            await self._reject_cycle(directory, parent)
            directory.set_parent_id(parent.id if parent else None, actor)
        if data.name is not None:
            directory.set_name(data.name, actor)
        if data.status is not None:
            directory.set_status(data.status, actor)

        await commit_or_conflict(self._session, DUPLICATE)
        return DirectoryResponse.from_model(directory, parent.external_id if parent else None)

    async def _parent_of(self, directory: Directory) -> Directory | None:
        return await self._directories.get(directory.parent_id) if directory.parent_id else None

    async def _active_parent(self, parent_id: UUID | None) -> Directory | None:
        if parent_id is None:
            return None
        found = await self._directories.get_by_external_id(parent_id)
        parent = require(found, "Directory", parent_id)
        if parent.status is not Status.ACTIVE:
            raise ConflictError(f"Directory {parent_id} is inactive")
        return parent

    async def _reject_cycle(self, directory: Directory, new_parent: Directory | None) -> None:
        """Walks up from the new parent one SELECT per level; meeting `directory` is a cycle."""
        node = new_parent
        while node is not None:
            if node.id == directory.id:
                raise InvalidRequestError("A directory cannot move under itself or a descendant")
            node = await self._parent_of(node)
