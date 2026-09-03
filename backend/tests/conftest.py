"""Shared pytest fixtures.

`client` is session-scoped and entered as a context manager (`with TestClient(app) as c`) so
every request in the test session runs on the same anyio event loop/portal. Without this, each
bare `TestClient(app).get(...)` call can spin up its own loop, and the async SQLAlchemy engine's
pooled connections — created on the first loop — then fail with "attached to a different loop"
on any later request that touches the database.

RATE_LIMIT_ENABLED is forced off before `app.main` is imported: every test in this suite reuses
the same session-scoped TestClient, which means the same client IP for every single request
(Starlette's TestClient always reports "testclient" as request.client.host) — dozens of tests
calling /auth/register or /auth/login across the whole run would otherwise trip the real
brute-force limits meant for one real client. tests/test_rate_limit.py re-enables it deliberately,
scoped to just that file, to test the limiter itself.
"""

import os

import pytest

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
