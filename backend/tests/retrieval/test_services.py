"""Business rules (ids refer to metric/test_cases_and_metrics.yml, retrieval section)."""

from uuid import uuid4

import pytest

from app.constants.status import Status
from app.errors import ConflictError, InvalidRequestError, NotFoundError
from app.retrieval.core.storage import (
    GcpStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)
from app.retrieval.models import ChunkState, Provider, StateStatus, UploadStatus
from app.retrieval.schemas.chunk import ChunkCreate, ChunkUpdate
from app.retrieval.schemas.directory import DirectoryCreate, DirectoryResponse, DirectoryUpdate
from app.retrieval.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from tests.retrieval.fakes import FakeDb

ACTOR = uuid4()
OTHER = uuid4()
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db() -> FakeDb:
    return FakeDb()


async def new_dir(db: FakeDb, name: str = "root", parent: object = None) -> DirectoryResponse:
    return await db.directories.create(DirectoryCreate(name=name, parent_id=parent), ACTOR)


def doc_body(directory: DirectoryResponse, **over: object) -> DocumentCreate:
    fields: dict[str, object] = {
        "name": "a.pdf",
        "document_type": "policy",
        "file_type": "pdf",
        "content_type": "application/pdf",
        "size_in_bytes": 10,
        "directory_id": directory.id,
        "chunking_strategy": "structure_aware",
        "embedding_model": "text-embedding",
        "provider": Provider.AWS,
        "bucket": "b",
        "storage_path": "x/a.pdf",
    }
    return DocumentCreate(**{**fields, **over})


async def new_doc(db: FakeDb, directory: DirectoryResponse | None = None) -> DocumentResponse:
    directory = directory or await new_dir(db)
    return await db.documents.create(doc_body(directory), ACTOR)


def chunk_body(**over: object) -> ChunkCreate:
    fields: dict[str, object] = {
        "state": ChunkState.CHUNKING,
        "state_status": StateStatus.IN_PROGRESS,
        "content": "hello",
        "content_checksum": "abc",
        "metadata": {"page": 1},
    }
    return ChunkCreate(**{**fields, **over})


# ---- directories


async def test_create_root_and_child(db: FakeDb) -> None:  # HP-1, HP-2
    root = await new_dir(db)
    assert (root.status, root.parent_id, root.created_by, root.updated_by) == (
        Status.ACTIVE,
        None,
        ACTOR,
        ACTOR,
    )
    child = await new_dir(db, "child", root.id)
    assert child.parent_id == root.id


async def test_directory_update_each_field(db: FakeDb) -> None:  # HP-3, D7
    root, other = await new_dir(db, "root"), await new_dir(db, "other")
    child = await new_dir(db, "child", root.id)
    renamed = await db.directories.update(child.id, DirectoryUpdate(name="renamed"), OTHER)
    assert (renamed.name, renamed.parent_id, renamed.updated_by) == ("renamed", root.id, OTHER)
    moved = await db.directories.update(child.id, DirectoryUpdate(parent_id=other.id), ACTOR)
    assert moved.parent_id == other.id
    to_root = await db.directories.update(child.id, DirectoryUpdate(parent_id=None), ACTOR)
    assert to_root.parent_id is None
    off = await db.directories.update(child.id, DirectoryUpdate(status=Status.INACTIVE), ACTOR)
    assert off.status is Status.INACTIVE


async def test_directory_empty_patch_changes_nothing(db: FakeDb) -> None:  # HP-8
    root = await new_dir(db)
    same = await db.directories.update(root.id, DirectoryUpdate(), OTHER)
    assert (same.name, same.updated_by) == ("root", ACTOR)


async def test_directory_unknown_parent_404(db: FakeDb) -> None:  # D1
    with pytest.raises(NotFoundError):
        await new_dir(db, "x", uuid4())
    root = await new_dir(db)
    with pytest.raises(NotFoundError):
        await db.directories.update(root.id, DirectoryUpdate(parent_id=uuid4()), ACTOR)


async def test_directory_unknown_404(db: FakeDb) -> None:  # D9
    with pytest.raises(NotFoundError):
        await db.directories.update(uuid4(), DirectoryUpdate(name="x"), ACTOR)


async def test_directory_self_parent_and_cycle_422(db: FakeDb) -> None:  # D5, D6
    a = await new_dir(db, "a")
    b = await new_dir(db, "b", a.id)
    c = await new_dir(db, "c", b.id)
    with pytest.raises(InvalidRequestError):
        await db.directories.update(a.id, DirectoryUpdate(parent_id=a.id), ACTOR)
    with pytest.raises(InvalidRequestError):
        await db.directories.update(a.id, DirectoryUpdate(parent_id=c.id), ACTOR)


async def test_directory_inactive_parent_409(db: FakeDb) -> None:  # D8
    root = await new_dir(db)
    db.deactivate_directory(root.id)
    with pytest.raises(ConflictError):
        await new_dir(db, "child", root.id)
    other = await new_dir(db, "other")
    with pytest.raises(ConflictError):
        await db.directories.update(other.id, DirectoryUpdate(parent_id=root.id), ACTOR)


# ---- documents


async def test_create_document_defaults(db: FakeDb) -> None:  # HP-4
    doc = await new_doc(db)
    assert (doc.upload_status, doc.status, doc.version) == (
        UploadStatus.INITIATED,
        Status.ACTIVE,
        1,
    )
    assert (doc.etag, doc.raw_storage_url, doc.created_by) == (None, None, ACTOR)


async def test_create_document_directory_rules(db: FakeDb) -> None:  # DO1, DO2
    directory = await new_dir(db)
    with pytest.raises(NotFoundError):
        await db.documents.create(doc_body(directory, directory_id=uuid4()), ACTOR)
    db.deactivate_directory(directory.id)
    with pytest.raises(ConflictError):
        await db.documents.create(doc_body(directory), ACTOR)


async def test_document_update_each_field_bumps_version(db: FakeDb) -> None:  # HP-5, DO11
    doc = await new_doc(db)
    other = await new_dir(db, "other")
    updated = await db.documents.update(
        doc.id,
        DocumentUpdate(
            name="b.pdf",
            directory_id=other.id,
            etag="e1",
            raw_storage_url="s3://b/x",
            upload_status=UploadStatus.SUCCESS,
            status=Status.INACTIVE,
        ),
        OTHER,
    )
    assert (updated.name, updated.directory_id, updated.etag) == ("b.pdf", other.id, "e1")
    assert (updated.raw_storage_url, updated.upload_status) == ("s3://b/x", UploadStatus.SUCCESS)
    assert (updated.status, updated.version, updated.updated_by) == (Status.INACTIVE, 2, OTHER)
    again = await db.documents.update(doc.id, DocumentUpdate(name="c.pdf"), ACTOR)
    assert again.version == 3


async def test_document_empty_patch_keeps_version(db: FakeDb) -> None:  # HP-8
    doc = await new_doc(db)
    same = await db.documents.update(doc.id, DocumentUpdate(), OTHER)
    assert (same.version, same.updated_by) == (1, ACTOR)


async def test_document_update_errors(db: FakeDb) -> None:  # DO1, DO2, DO8
    doc = await new_doc(db)
    with pytest.raises(NotFoundError):
        await db.documents.update(uuid4(), DocumentUpdate(name="x"), ACTOR)
    with pytest.raises(NotFoundError):
        await db.documents.update(doc.id, DocumentUpdate(directory_id=uuid4()), ACTOR)
    inactive = await new_dir(db, "off")
    db.deactivate_directory(inactive.id)
    with pytest.raises(ConflictError):
        await db.documents.update(doc.id, DocumentUpdate(directory_id=inactive.id), ACTOR)


async def test_same_document_name_allowed(db: FakeDb) -> None:  # DO10
    directory = await new_dir(db)
    await db.documents.create(doc_body(directory), ACTOR)
    await db.documents.create(doc_body(directory), ACTOR)


# ---- chunks


async def test_add_chunk(db: FakeDb) -> None:  # HP-6, C7
    doc = await new_doc(db)
    chunk = await db.chunks.add(doc.id, chunk_body(), ACTOR)
    assert (chunk.status, chunk.version, chunk.changes, chunk.created_by) == (
        Status.ACTIVE,
        1,
        [],
        ACTOR,
    )
    assert chunk.document_id == doc.id and chunk.id in db.chunks_repo.docs
    assert db.chunks_repo.docs[chunk.id].source["chunk_id"] == chunk.id


async def test_add_chunk_document_rules(db: FakeDb) -> None:  # C1, C2
    with pytest.raises(NotFoundError):
        await db.chunks.add(uuid4(), chunk_body(), ACTOR)
    doc = await new_doc(db)
    db.deactivate_document(doc.id)
    with pytest.raises(ConflictError):
        await db.chunks.add(doc.id, chunk_body(), ACTOR)


async def test_update_chunk_status(db: FakeDb) -> None:  # HP-7
    doc = await new_doc(db)
    chunk = await db.chunks.add(doc.id, chunk_body(), ACTOR)
    updated = await db.chunks.update(doc.id, chunk.id, ChunkUpdate(status=Status.INACTIVE), OTHER)
    assert (updated.status, updated.version, updated.updated_by) == (Status.INACTIVE, 2, OTHER)
    assert updated.content == "hello" and updated.created_by == ACTOR
    assert db.chunks_repo.docs[chunk.id].source["status"] == "INACTIVE"


async def test_update_chunk_not_found_rules(db: FakeDb) -> None:  # C5, C6
    doc, other_doc = await new_doc(db), await new_doc(db)
    chunk = await db.chunks.add(doc.id, chunk_body(), ACTOR)
    with pytest.raises(NotFoundError):
        await db.chunks.update(doc.id, "missing", ChunkUpdate(status=Status.INACTIVE), ACTOR)
    with pytest.raises(NotFoundError):
        await db.chunks.update(other_doc.id, chunk.id, ChunkUpdate(status=Status.INACTIVE), ACTOR)
    with pytest.raises(NotFoundError):
        await db.chunks.update(uuid4(), chunk.id, ChunkUpdate(status=Status.INACTIVE), ACTOR)


# ---- storage stubs


async def test_storage_providers_are_empty() -> None:  # S1
    assert isinstance(get_storage_provider(Provider.AWS), S3StorageProvider)
    assert isinstance(get_storage_provider(Provider.GCP), GcpStorageProvider)
    for provider in (S3StorageProvider(), GcpStorageProvider()):
        with pytest.raises(Exception, match="not implemented") as err:
            await provider.upload("b", "p", b"", "text/plain")
        assert err.value.status_code == 501  # type: ignore[attr-defined]
