"""Shared FastAPI dependencies: DB session (re-exported from app.core.db) and the
authenticated-user dependency every non-public route depends on.
"""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.errors import NotFoundError, UnauthorizedError
from app.core.security import JWTError, decode_access_token
from app.models import User
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedError("Not an access token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    # Eager-load `profile` — under AsyncSession, an un-loaded lazy relationship can only be
    # accessed from inside an active `await session.*()` greenlet context. A bare `user.profile`
    # touched later (e.g. by response-model serialization, or a route reading it directly) would
    # raise MissingGreenlet otherwise.
    user = (
        await db.execute(select(User).options(selectinload(User.profile)).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def require_role(*allowed: UserRole):
    """Dependency factory guarding a route by role (docs/DECISIONS.md D-30, D-112).

    Insufficient role answers **404, not 403**. A 403 would confirm that an admin surface exists
    at that path, which is exactly what someone probing for one wants to learn; 404 makes the
    admin API indistinguishable from empty space. Missing or invalid credentials still answer
    401 — that is about the caller's token, not about what exists on the server.
    """

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise NotFoundError("NOT_FOUND", "Not found")
        return user

    return dependency


# Named guards for the two role sets that exist today. `trainer` is reserved in the enum but
# nothing grants it yet (D-30), so nothing guards by it either.
get_current_admin = require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
get_current_super_admin = require_role(UserRole.SUPER_ADMIN)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """For public endpoints (e.g. exercise browsing) that want to personalize the response
    (favorite status) when a token is present, but must not fail without one."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except UnauthorizedError:
        return None
