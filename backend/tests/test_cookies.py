"""The refresh cookie's attribute string (docs/DECISIONS.md D-13).

Asserted directly rather than through a request because httpx's cookie jar refuses `Secure`
cookies over the `http://testserver` origin TestClient uses — so the suite runs with
`COOKIE_SECURE=false` and the production shape is checked here instead. These four attributes are
the whole security argument for the cookie, and a silent regression in any of them would not fail
any other test.
"""

import pytest

from app.core import cookies


class _Settings:
    def __init__(self, secure: bool) -> None:
        self.cookie_secure = secure


@pytest.fixture
def secure(monkeypatch):
    monkeypatch.setattr(cookies, "settings", _Settings(True))


@pytest.fixture
def insecure(monkeypatch):
    monkeypatch.setattr(cookies, "settings", _Settings(False))


def test_production_cookie_carries_every_required_attribute(secure) -> None:
    header = f"{cookies.cookie_name()}=value; {cookies._attributes(3600)}"

    assert header.startswith("__Host-")
    assert "Path=/" in header          # __Host- requires it
    assert "Secure" in header          # __Host- requires it, and SameSite=None requires it
    assert "HttpOnly" in header        # D-12: script must never read the refresh token
    assert "SameSite=None" in header   # Telegram Web runs the Mini App in a cross-site iframe
    assert "Partitioned" in header     # CHIPS: survives Chrome's third-party cookie blocking
    # A Domain attribute would void the __Host- prefix and let a sibling subdomain plant cookies.
    assert "Domain=" not in header


def test_insecure_local_mode_drops_the_host_prefix_with_secure(insecure) -> None:
    """`__Host-` is meaningless without Secure, so a plain-HTTP local run must not claim it."""
    header = f"{cookies.cookie_name()}=value; {cookies._attributes(3600)}"

    assert not cookies.cookie_name().startswith("__Host-")
    assert "Secure" not in header
    assert "Partitioned" not in header
    assert "SameSite=Lax" in header
    assert "HttpOnly" in header  # still never readable by script


def test_clearing_sets_a_zero_max_age(secure) -> None:
    assert "Max-Age=0" in cookies._attributes(0)
