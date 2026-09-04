"""Shared pytest fixtures.

`client` is session-scoped and entered as a context manager (`with TestClient(app) as c`) so
every request in the test session runs on the same anyio event loop/portal. Without this, each
bare `TestClient(app).get(...)` call can spin up its own loop, and the async SQLAlchemy engine's
pooled connections — created on the first loop — then fail with "attached to a different loop"
on any later request that touches the database.

Environment set before `app.main` is imported:

* `RATE_LIMIT_ENABLED=false` — every test reuses one TestClient, and Starlette reports the same
  `request.client.host` ("testclient") for all of them, so dozens of auth calls across the run
  would otherwise trip limits meant for one real client. tests/test_rate_limit.py re-enables it
  deliberately, scoped to itself.
* `TELEGRAM_BOT_TOKEN` — a known value so tests can sign `initData` exactly as Telegram would and
  get a real, verifiable match. Never a production secret.
* `BOT_SHARED_SECRET` — the bot's door requires it (D-20) and fails closed when unset, so the
  suite has to supply one.
* `COOKIE_SECURE=false` — httpx's cookie jar refuses `Secure` cookies over the `http://testserver`
  origin TestClient uses, which would make every cookie-flow test fail for a reason that has
  nothing to do with the code. The production attribute string is asserted directly instead, in
  tests/test_cookies.py.
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from urllib.parse import urlencode

import pytest

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-bot-token")
os.environ.setdefault("BOT_SHARED_SECRET", "test-bot-shared-secret")
os.environ.setdefault("COOKIE_SECURE", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BOT_SECRET = os.environ["BOT_SHARED_SECRET"]
BOT_HEADERS = {"X-Bot-Secret": BOT_SECRET}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def new_telegram_id() -> int:
    """Telegram user ids are real int64s; a random one keeps tests independent."""
    return uuid.uuid4().int % (10**9)


def sign_init_data(fields: dict, bot_token: str = BOT_TOKEN) -> str:
    """Build a real `initData` string for `fields`, signed the way Telegram signs it.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": computed})


def make_init_data(
    telegram_id: int,
    *,
    username: str | None = "smoketest",
    first_name: str = "Smoke",
    auth_date: int | None = None,
    language_code: str | None = None,
    bot_token: str = BOT_TOKEN,
) -> str:
    user: dict = {"id": telegram_id, "first_name": first_name}
    if username:
        user["username"] = username
    if language_code:
        user["language_code"] = language_code
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user, separators=(",", ":")),
    }
    return sign_init_data(fields, bot_token)


@pytest.fixture
def telegram_id() -> int:
    return new_telegram_id()


@pytest.fixture
def auth_headers(client, telegram_id):
    """A signed-in ordinary user, as bearer headers.

    The refresh cookie is dropped afterwards because `client` is session-scoped: leaving cookies
    in its jar would let one test's session leak into the next one's requests.
    """
    response = client.post("/api/v1/auth/telegram-webapp", json={"init_data": make_init_data(telegram_id)})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}
