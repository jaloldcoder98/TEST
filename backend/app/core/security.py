"""Token minting and verification.

Two token types, deliberately asymmetric (docs/DECISIONS.md D-12, D-13, D-14):

* **Access** — short-lived, signed with `jwt_secret`, carries the role so route guards do not
  need a database round-trip to reject an obviously unauthorised caller. Lives only in the
  client's memory.
* **Refresh** — longer-lived, signed with a *different* secret so a leaked access token cannot be
  reshaped into a refresh token, and recorded server-side by hash (`app.models.user.RefreshToken`)
  so it can be revoked. Reaches the browser only as an httpOnly cookie.

There is no password hashing here any more: Telegram is the only identity (D-10).
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings
from app.models.enums import UserRole

settings = get_settings()

# Admin sessions expire faster than ordinary ones. The account that can grant roles and run bulk
# imports is the one worth stealing, so it gets the shortest window we can live with.
_ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN}


def hash_token(token: str) -> str:
    """SHA-256 is enough here — refresh tokens are already high-entropy random JWTs; this is
    just so a DB leak doesn't hand out valid bearer tokens directly."""
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(refresh_token: str) -> str:
    """Derive the double-submit CSRF token from the refresh token (D-19).

    Derived rather than stored: the value is reproducible from the cookie the browser already
    holds, so verification needs no extra column and no lookup, and there is no second secret to
    keep in sync with the session. An attacker cannot compute it because the refresh token it is
    derived from is httpOnly and never visible to script.
    """
    return hmac.new(
        settings.jwt_secret.encode(), hash_token(refresh_token).encode(), hashlib.sha256
    ).hexdigest()


def access_token_lifetime(role: UserRole) -> timedelta:
    if role in _ADMIN_ROLES:
        return timedelta(minutes=settings.admin_access_token_expire_minutes)
    return timedelta(minutes=settings.access_token_expire_minutes)


def refresh_token_lifetime(role: UserRole) -> timedelta:
    if role in _ADMIN_ROLES:
        return timedelta(hours=settings.admin_refresh_token_expire_hours)
    return timedelta(days=settings.refresh_token_expire_days)


def create_access_token(user_id: uuid.UUID, role: UserRole = UserRole.USER) -> str:
    """`exp` has one-second resolution, so two tokens minted for the same user in the same second
    would otherwise be byte-identical — indistinguishable in logs, and impossible to address
    individually if per-token revocation is ever needed. The `jti` costs nothing and removes that."""
    expire = datetime.now(timezone.utc) + access_token_lifetime(role)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "role": role.value,
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: uuid.UUID, family_id: uuid.UUID, role: UserRole = UserRole.USER
) -> tuple[str, datetime]:
    """Mint a refresh token belonging to `family_id`.

    The family travels in the payload as well as the database row so a presented token names its
    own chain even before we look it up — useful when the lookup is exactly what fails.
    """
    expire = datetime.now(timezone.utc) + refresh_token_lifetime(role)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "fam": str(family_id),
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm=settings.jwt_algorithm), expire


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])


__all__ = [
    "JWTError",
    "hash_token",
    "csrf_token_for",
    "access_token_lifetime",
    "refresh_token_lifetime",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
]
