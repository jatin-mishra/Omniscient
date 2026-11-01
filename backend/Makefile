.PHONY: dev test lint fmt typecheck infra-up infra-down init-storage test-integration

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest -q

lint:
	uv run ruff check .

fmt:
	uv run ruff check --select I --fix . && uv run ruff format .

typecheck:
	uv run mypy app

infra-up:
	docker compose up -d --wait

infra-down:
	docker compose down

init-storage:
	uv run python -m app.scripts.init_storage

test-integration:
	uv run pytest -q -m integration
