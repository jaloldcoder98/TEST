"""Shared pytest fixtures.

`client` is session-scoped and entered as a context manager (`with TestClient(app) as c`) so
every request in the test session runs on the same anyio event loop/portal. Without this, each
bare `TestClient(app).get(...)` call can spin up its own loop, and the async SQLAlchemy engine's
pooled connections — created on the first loop — then fail with "attached to a different loop"
on any later request that touches the database.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
