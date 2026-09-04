"""CSRF protection for the one endpoint that authenticates from a cookie (docs/DECISIONS.md D-19).

Every other route authenticates from an `Authorization: Bearer` header, which a cross-site page
cannot set — so the CSRF surface of this API is exactly `POST /auth/refresh` and `POST /auth/logout`.

Three layers, in the order they matter:

1. **The cookie is used nowhere else.** Shrinking the surface to one endpoint is worth more than
   any check applied to a large one.
2. **Double-submit token, sent in a header.** Authoritative. The client stores the CSRF token in
   memory alongside the access token and echoes it in `X-CSRF-Token`; an attacker's page can make
   the browser send the cookie but cannot make it send this header cross-origin.
3. **Origin / Referer.** Secondary, and deliberately fail-*open* when both are absent. Phase 0
   exists partly to find out whether every Telegram client sends them; until that is measured,
   treating their absence as an attack would lock out real users on whichever client omits them.
   When a header *is* present it must match, because a mismatched Origin is a real signal.
"""

from urllib.parse import urlsplit

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()


class CSRFError(AppError):
    def __init__(self, message: str = "CSRF validation failed") -> None:
        super().__init__("CSRF_FAILED", message, 403)


def _allowed_origins() -> set[str]:
    origins = {o.rstrip("/") for o in settings.cors_origins_list}
    if settings.frontend_url:
        origins.add(settings.frontend_url.rstrip("/"))
    return origins


def _origin_of(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def verify_csrf(request: Request, expected_token: str | None) -> None:
    """Raise unless this request may act on the refresh cookie.

    `expected_token` is the CSRF token bound to the session server-side; `None` means the session
    predates CSRF binding, which is only reachable for a token minted by an older build and is
    rejected rather than waved through.
    """
    presented = request.headers.get("x-csrf-token")
    if not expected_token or not presented or not _constant_time_equals(presented, expected_token):
        raise CSRFError("Missing or invalid CSRF token")

    allowed = _allowed_origins()
    if not allowed:
        return

    for header in ("origin", "referer"):
        origin = _origin_of(request.headers.get(header))
        if origin is None:
            continue  # layer 3 is advisory — see the module docstring
        if origin.rstrip("/") not in allowed:
            raise CSRFError(f"Request {header} is not an allowed origin")


def _constant_time_equals(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)
