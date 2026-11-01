# omniscient

FastAPI service scaffolded from the `fastapi-python` skill.

## Run

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
curl -i http://127.0.0.1:8000/health
```

## Quality gates

```bash
make test        # pytest
make lint        # ruff check
make typecheck   # mypy --strict
make fmt         # ruff format + import sort
```

## Storage (Postgres + Elasticsearch)

```bash
make infra-up          # postgres:16 + elasticsearch:8 via docker compose
make init-storage      # create table `documents` and index `chunks` (idempotent)
make test-integration  # tests against the real stores
curl -i http://127.0.0.1:8000/health/ready
```

Env vars (defaults match docker-compose): `DATABASE_URL`, `ELASTICSEARCH_URL`, `ES_CHUNKS_INDEX`.
Schema is created with `create_all`; switch to Alembic before the first real schema change.

## Layout

```
app/
  main.py            app factory, lifespan, middleware, routers
  core/config.py     typed settings (env + .env), cached
  core/logging.py    stdlib logging with request id on every line
  core/errors.py     AppError + JSON error envelope
  middleware/        pure-ASGI request-id middleware
  api/               routers (health at /health; add versioned routers under api/v1/)
  schemas/           pydantic request/response models
  db/                engine/session factory, ES client, ORM models
  repositories/      data access for documents (PG) and chunks (ES)
  scripts/           one-off CLIs (init_storage)
tests/               TestClient-based tests
```

## Conventions

- `create_app()` is the only place that wires middleware, handlers and routers.
- Settings come from `get_settings()`; never read `os.environ` elsewhere.
- Raise `AppError` (or a subclass) for expected failures; the handler renders
  `{"error": {"code", "message", "request_id"}}`. Unexpected exceptions become a
  generic 500 with the same envelope and a full traceback in the logs.
- Every response carries `X-Request-ID` (echoed from the request if present).

Commit `uv.lock`; the Dockerfile installs with `--locked`.
