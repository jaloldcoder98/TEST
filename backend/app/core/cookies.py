"""The refresh cookie, in one place (docs/DECISIONS.md D-13, D-15).

Written by hand rather than through `response.set_cookie` because `Partitioned` is not supported
uniformly across Starlette versions, and because the exact attribute string is a decision worth
being able to read at a glance rather than reconstructing from keyword arguments.

The `__Host-` prefix is the part that does real work: a browser accepts such a cookie only when
it is `Secure`, has `Path=/`, and carries **no** `Domain` — which means a compromised sibling
subdomain cannot plant one. The prefix requires Secure, so a plain-HTTP local run (where
`cookie_secure` is false) has to fall back to an unprefixed name; production never does.
"""

from fastapi import Request, Response

from app.core.config import get_settings

settings = get_settings()

_SECURE_NAME = "__Host-gym_refresh"
_INSECURE_NAME = "gym_refresh"


def cookie_name() -> str:
    return _SECURE_NAME if settings.cookie_secure else _INSECURE_NAME


def _attributes(max_age: int) -> str:
    parts = ["Path=/", "HttpOnly", f"Max-Age={max_age}"]
    if settings.cookie_secure:
        # SameSite=None is required for Telegram Web, where the Mini App runs in a cross-site
        # iframe; Partitioned (CHIPS) is what keeps Chrome from dropping it there once
        # third-party cookies are blocked. Both demand Secure, so they travel together.
        parts += ["Secure", "SameSite=None", "Partitioned"]
    else:
        parts.append("SameSite=Lax")
    return "; ".join(parts)


def set_refresh_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.headers.append("Set-Cookie", f"{cookie_name()}={token}; {_attributes(max_age_seconds)}")


def clear_refresh_cookie(response: Response) -> None:
    response.headers.append("Set-Cookie", f"{cookie_name()}=; {_attributes(0)}")


def read_refresh_cookie(request: Request) -> str | None:
    """Both names are read so a deployment that flips `cookie_secure` does not strand sessions
    issued under the other one."""
    return request.cookies.get(_SECURE_NAME) or request.cookies.get(_INSECURE_NAME)
