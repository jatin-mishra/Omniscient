import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Unit tests must not need Postgres/ES; integration tests create the schema themselves.
os.environ.setdefault("CREATE_SCHEMA_ON_STARTUP", "false")

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Context manager runs the lifespan; raise_server_exceptions=False lets us assert on 500s.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()
