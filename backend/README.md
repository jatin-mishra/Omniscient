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
make test-integration  # tests against the real stores
curl -i http://127.0.0.1:8000/health/ready
```

Env vars (defaults match docker-compose): `DATABASE_URL`, `ELASTICSEARCH_URL`, `ES_CHUNKS_INDEX`,
`CREATE_SCHEMA_ON_STARTUP` (default `true`).
On startup the app creates missing tables and the `chunks` index (idempotent `create_all`).
`create_all` never alters existing tables: a column change needs manual DDL or a migration tool.

## Layout

```
app/
  main.py            app factory, lifespan (creates schema), middleware, routers
  router.py          global router: /health + every module under /v1
  config.py          typed settings (env + .env), cached
  logging.py         stdlib logging with request id on every line
  errors.py          AppError (+ NotFound, Conflict) and the JSON error envelope
  health.py          /health, /health/ready
  middlewares/       pure-ASGI request-id middleware
  db/                shared infra: Base + mixins, engine/session, ES client, deps
  onboarding/        teams, users, groups, group-users
  retrieval/         documents, query, search
  policy_engine/  audit/  tracker/   (empty skeletons)
tests/               TestClient-based tests; integration/ needs docker-compose
```

Each business module has the same shape: `api/` (routers), `core/` (business rules,
owns the commit), `models/` (ORM), `schemas/` (pydantic), `repositories/` (plain
select / insert / update, never commit) and `deps.py`. Modules import only the global
layer, never each other (enforced by `tests/test_module_boundaries.py`), so any module
can be extracted into its own service.

## Conventions

- `create_app()` is the only place that wires middleware, handlers and routers.
- Settings come from `get_settings()`; never read `os.environ` elsewhere.
- Raise `AppError` (or a subclass) for expected failures; the handler renders
  `{"error": {"code", "message", "request_id"}}`. Unexpected exceptions become a
  generic 500 with the same envelope and a full traceback in the logs.
- Every response carries `X-Request-ID` (echoed from the request if present).

Commit `uv.lock`; the Dockerfile installs with `--locked`.
