"""Business rules for workflows, embeddings and chunk-vectors (ids: metric file, Temporal +
ChunkVector section)."""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from temporalio.client import Client
from temporalio.testing import ActivityEnvironment

from app.config import Settings, get_settings
from app.constants.status import Status
from app.errors import ConflictError, InvalidRequestError, NotFoundError
from app.retrieval.core.chunk_vector_service import ChunkVectorService
from app.retrieval.core.embedding import ConstantEmbeddingProvider, get_embedding_provider
from app.retrieval.core.workflow_service import WorkflowService
from app.retrieval.errors import EmbeddingFailedError, WorkflowUnavailableError
from app.retrieval.models import ChunkVector
from app.retrieval.schemas.chunk_vector import ChunkVectorCreate
from app.retrieval.temporal.activities import log_activity
from app.retrieval.temporal.client import create_temporal_client, ping_temporal
from app.retrieval.temporal.workflows import LogWorkflow
from tests.onboarding.fakes import FakeRepo, FakeSession
from tests.retrieval.fakes import FakeDb

ACTOR = uuid4()
DIM = 4
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# ---- config -------------------------------------------------------------------------------


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:  # T1
    for key in list(__import__("os").environ):
        if key.startswith(("TEMPORAL_", "EMBEDDING_", "WORKFLOW_")):
            monkeypatch.delenv(key)
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (s.temporal_address, s.temporal_namespace) == ("localhost:7233", "default")
    assert s.temporal_task_queue == "retrieval" and s.embedding_dimensions == 1536
    assert (s.temporal_connect_timeout_s, s.temporal_rpc_timeout_s) == (5.0, 10.0)
    assert s.workflow_execution_timeout_s == 300.0 and s.temporal_api_key == ""


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:  # T1
    monkeypatch.setenv("TEMPORAL_ADDRESS", "t:1")
    monkeypatch.setenv("TEMPORAL_RPC_TIMEOUT_S", "2.5")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "8")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (s.temporal_address, s.temporal_rpc_timeout_s, s.embedding_dimensions) == ("t:1", 2.5, 8)


@pytest.mark.parametrize(
    "field",
    [
        "temporal_connect_timeout_s",
        "temporal_rpc_timeout_s",
        "workflow_execution_timeout_s",
        "embedding_dimensions",
    ],
)
@pytest.mark.parametrize("value", [0, -1])
def test_settings_reject_non_positive(field: str, value: int) -> None:  # T2
    with pytest.raises(ValueError, match=field):
        Settings(_env_file=None, **{field: value})  # type: ignore[call-arg, arg-type]


async def test_client_config_from_settings() -> None:  # T3, L1
    plain = await create_temporal_client(Settings(_env_file=None))  # type: ignore[call-arg]
    assert plain.service_client.config.api_key is None  # empty key = no auth
    assert plain.service_client.config.lazy is True  # no connection at build time
    secured = await create_temporal_client(
        Settings(_env_file=None, temporal_api_key="k", temporal_tls=True)  # type: ignore[call-arg]
    )
    assert secured.service_client.config.api_key == "k"
    assert secured.service_client.config.tls


async def test_ping_false_when_unreachable() -> None:  # L4
    s = Settings(_env_file=None, temporal_address="127.0.0.1:1")  # type: ignore[call-arg]
    assert await ping_temporal(await create_temporal_client(s), 0.5) is False


def test_app_boots_without_temporal(client: Any) -> None:  # L1, L2, L3
    from app.main import app
    from app.retrieval.deps import get_temporal_client

    assert isinstance(app.state.temporal, Client)
    app.dependency_overrides[get_temporal_client] = lambda: "fake"
    assert client.get("/health").status_code == 200


# ---- workflow trigger ---------------------------------------------------------------------


class FakeTemporal:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error = error

    async def start_workflow(self, workflow: Any, arg: Any, **kwargs: Any) -> None:
        if self.error:
            raise self.error
        self.calls.append({"workflow": workflow, "arg": arg, **kwargs})


def workflows(client: FakeTemporal) -> WorkflowService:
    return WorkflowService(
        client,  # type: ignore[arg-type]
        "q",
        timedelta(seconds=30),
        timedelta(seconds=3),
    )


async def test_trigger_starts_workflow_with_configured_timeouts() -> None:  # W1
    client = FakeTemporal()
    accepted = await workflows(client).trigger_log("hi")
    call = client.calls[0]
    assert call["id"] == accepted.workflow_id and call["task_queue"] == "q"
    assert call["arg"] == "hi" and call["workflow"] == LogWorkflow.run
    assert call["execution_timeout"] == timedelta(seconds=30)
    assert call["rpc_timeout"] == timedelta(seconds=3)


@pytest.mark.parametrize("error", [RuntimeError("down"), TimeoutError(), OSError("refused")])
async def test_trigger_failure_is_503(error: Exception) -> None:  # W4
    with pytest.raises(WorkflowUnavailableError) as exc:
        await workflows(FakeTemporal(error)).trigger_log("hi")
    assert exc.value.status_code == 503


async def test_trigger_ids_are_unique() -> None:  # W5
    service = workflows(FakeTemporal())
    ids = {(await service.trigger_log("hi")).workflow_id for _ in range(20)}
    assert len(ids) == 20


# ---- worker / activity --------------------------------------------------------------------


async def test_activity_logs_message(caplog: pytest.LogCaptureFixture) -> None:  # K1
    caplog.set_level("INFO", logger="app.retrieval.temporal.activities")
    await ActivityEnvironment().run(log_activity, "hello")
    assert "hello" in caplog.text


# K2 (worker registration/shutdown) and K3 (sandbox determinism) need a Temporal server:
# covered by tests/integration/test_temporal_vectors.py


# ---- embedding provider -------------------------------------------------------------------


async def test_constant_provider() -> None:  # E1, E2
    provider = ConstantEmbeddingProvider(DIM)
    first, second = await provider.embed("a"), await provider.embed("b")
    assert len(first) == DIM and first == second and len(set(first)) == 1
    first.append(9.0)  # callers cannot mutate the stub's vector
    assert len(await provider.embed("a")) == DIM


def test_provider_factory() -> None:  # E3
    assert isinstance(get_embedding_provider("constant", DIM), ConstantEmbeddingProvider)
    with pytest.raises(InvalidRequestError):
        get_embedding_provider("nope", DIM)


# ---- chunk vector -------------------------------------------------------------------------


class SpyProvider:
    def __init__(self, vector: list[float] | None = None, error: Exception | None = None) -> None:
        self.vector = vector if vector is not None else [0.5] * DIM
        self.error = error
        self.texts: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        if self.error:
            raise self.error
        return self.vector


class CountingSession(FakeSession):
    def __init__(self, fail: bool = False) -> None:
        self.commits, self.rollbacks, self.fail = 0, 0, fail

    async def commit(self) -> None:
        self.commits += 1
        if self.fail:
            raise IntegrityError("insert", {}, Exception("duplicate"))

    async def rollback(self) -> None:
        self.rollbacks += 1


async def make_document(db: FakeDb) -> Any:
    from tests.retrieval.test_services import doc_body, new_dir

    return await db.documents.create(doc_body(await new_dir(db)), ACTOR)


def vectors(
    db: FakeDb, provider: SpyProvider, session: CountingSession | None = None
) -> tuple[ChunkVectorService, FakeRepo[ChunkVector], CountingSession]:
    repo = FakeRepo[ChunkVector]()
    session = session or CountingSession()
    service = ChunkVectorService(
        session,  # type: ignore[arg-type]
        repo,  # type: ignore[arg-type]
        db.documents_repo,  # type: ignore[arg-type]
        provider,
        DIM,
    )
    return service, repo, session


async def test_add_vector_embeds_and_stores() -> None:  # V1, V2, V11
    db, provider = FakeDb(), SpyProvider()
    document = await make_document(db)
    service, repo, session = vectors(db, provider)
    res = await service.add(
        ChunkVectorCreate(chunk_id="c1", document_id=document.id, content="hello"), ACTOR
    )
    assert provider.texts == ["hello"]
    row = repo.rows[0]
    assert row.content == [0.5] * DIM and row.chunk_id == "c1"
    assert row.created_by == row.updated_by == ACTOR and row.status is Status.ACTIVE
    assert res.chunk_id == "c1" and res.document_id == document.id and res.id == row.external_id
    assert session.commits == 1


async def test_add_vector_unknown_document() -> None:  # V6
    db = FakeDb()
    service, repo, session = vectors(db, SpyProvider())
    with pytest.raises(NotFoundError):
        await service.add(ChunkVectorCreate(chunk_id="c", document_id=uuid4(), content="x"), ACTOR)
    assert repo.rows == [] and session.commits == 0


async def test_add_vector_inactive_document() -> None:  # V7
    db, provider = FakeDb(), SpyProvider()
    document = await make_document(db)
    db.deactivate_document(document.id)
    service, repo, _ = vectors(db, provider)
    with pytest.raises(ConflictError):
        await service.add(
            ChunkVectorCreate(chunk_id="c", document_id=document.id, content="x"), ACTOR
        )
    assert provider.texts == [] and repo.rows == []  # no embedding spent on a rejected request


async def test_add_vector_duplicate_chunk_is_conflict() -> None:  # V8
    db = FakeDb()
    document = await make_document(db)
    service, _, session = vectors(db, SpyProvider(), CountingSession(fail=True))
    with pytest.raises(ConflictError):
        await service.add(
            ChunkVectorCreate(chunk_id="c", document_id=document.id, content="x"), ACTOR
        )
    assert session.rollbacks == 1


@pytest.mark.parametrize("vector", [[0.1] * (DIM - 1), [0.1] * (DIM + 1), []])
async def test_add_vector_wrong_dimension(vector: list[float]) -> None:  # V9
    db = FakeDb()
    document = await make_document(db)
    service, repo, session = vectors(db, SpyProvider(vector))
    with pytest.raises(EmbeddingFailedError):
        await service.add(
            ChunkVectorCreate(chunk_id="c", document_id=document.id, content="x"), ACTOR
        )
    assert repo.rows == [] and session.commits == 0


async def test_add_vector_provider_error_persists_nothing() -> None:  # V10
    db = FakeDb()
    document = await make_document(db)
    service, repo, session = vectors(db, SpyProvider(error=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        await service.add(
            ChunkVectorCreate(chunk_id="c", document_id=document.id, content="x"), ACTOR
        )
    assert repo.rows == [] and session.commits == 0


# ---- model --------------------------------------------------------------------------------


def make_vector() -> ChunkVector:
    return ChunkVector(
        chunk_id="c",
        document_id=uuid4(),
        content=[0.1] * get_settings().embedding_dimensions,
        status=Status.ACTIVE,
        created_by=ACTOR,
        updated_by=ACTOR,
    )


def test_model_uses_standard_columns() -> None:  # M1
    cols = {c.name for c in ChunkVector.__table__.columns}
    assert {"id", "external_id", "chunk_id", "document_id", "content", "status"} <= cols
    assert {"created_at", "created_by", "updated_at", "updated_by"} <= cols
    assert ChunkVector.__table__.c.content.type.dim == get_settings().embedding_dimensions  # type: ignore[attr-defined]


def test_set_status() -> None:  # M2, M3
    vector, editor = make_vector(), uuid4()
    vector.set_status(Status.INACTIVE, editor)
    assert vector.status is Status.INACTIVE and vector.updated_by == editor
    assert vector.created_by == ACTOR
    vector.set_status(Status.INACTIVE, editor)  # idempotent
    assert vector.status is Status.INACTIVE
