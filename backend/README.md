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
make infra-up          # pgvector postgres:16 + elasticsearch:8 + temporal dev server
make test-integration  # tests against the real stores
curl -i http://127.0.0.1:8000/health/ready
```

Env vars (defaults match docker-compose): `DATABASE_URL`, `ELASTICSEARCH_URL`, `ES_CHUNKS_INDEX`,
`CREATE_SCHEMA_ON_STARTUP` (default `true`).
On startup the app creates missing tables and the `chunks` index (idempotent `create_all`).
`create_all` never alters existing tables: a column change needs manual DDL or a migration tool.
Upgrading from the old retrieval schema: `DROP TABLE documents;` in Postgres and delete the old
`chunks` index in Elasticsearch (`curl -X DELETE localhost:9200/chunks`), then restart.

## Temporal + vectors

The API starts workflows (`POST /v1/workflows/log` -> 202); a **separate worker** runs them:
`make worker` (or `docker compose --profile worker up worker`). The API client connects lazily, so
the app boots without Temporal (trigger returns 503, `/health/ready` reports it).
Env vars: `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_API_KEY`, `TEMPORAL_TLS`,
`TEMPORAL_TASK_QUEUE`, `TEMPORAL_CONNECT_TIMEOUT_S`, `TEMPORAL_RPC_TIMEOUT_S`,
`WORKFLOW_EXECUTION_TIMEOUT_S`.

`POST /v1/chunk-vectors` embeds the content (`EMBEDDING_PROVIDER=constant` stub for now) and stores
it in `chunk_vectors` (pgvector). `EMBEDDING_DIMENSIONS` (default 1536) fixes the column size at
table creation; changing it later means recreating the table. Postgres must be the pgvector image:
recreate an existing local volume (`docker compose down -v`) after switching.

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
  retrieval/         directories, documents, chunks
  policy_engine/     policies, user permissions
  tracker/           tickets (provider interface), status webhook
  audit/             (empty skeleton)
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

## Tracker webhook

`POST /v1/tickets/webhooks/{provider}` is called by the ticket system, not a user, so it has no
`X-User-Id`. It is authenticated by a signature: set `TRACKER_WEBHOOK_SECRET` and send
`X-Signature: HMAC-SHA256(secret, raw body)` as hex. With no secret configured every webhook is
rejected. Internal payload: `{"external_ticket_id": "...", "status": "open|in_progress|resolved|closed", "occurred_at": "<ISO-8601 with timezone>"}`;
events older than the last applied one are ignored.
