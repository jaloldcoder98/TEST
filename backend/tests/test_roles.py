"""Role guards (docs/DECISIONS.md D-30, D-112).

The behaviour worth pinning down is the 404: an admin route must be indistinguishable from a
path that does not exist, because a 403 tells someone probing that they found the right door.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_current_user, require_role
from app.core.errors import register_error_handlers
from app.models import User
from app.models.enums import UserRole


def _app_with_guard(*allowed: UserRole, current_role: UserRole) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    async def _fake_user() -> User:
        return User(username="fake", role=current_role, is_active=True)

    @app.get("/guarded", dependencies=[Depends(require_role(*allowed))])
    async def guarded() -> dict:
        return {"ok": True}

    app.dependency_overrides[get_current_user] = _fake_user
    return TestClient(app)


@pytest.mark.parametrize(
    "current_role,allowed,expected",
    [
        (UserRole.USER, (UserRole.ADMIN, UserRole.SUPER_ADMIN), 404),
        (UserRole.TRAINER, (UserRole.ADMIN, UserRole.SUPER_ADMIN), 404),
        (UserRole.ADMIN, (UserRole.ADMIN, UserRole.SUPER_ADMIN), 200),
        (UserRole.SUPER_ADMIN, (UserRole.ADMIN, UserRole.SUPER_ADMIN), 200),
        # Only super_admin may grant roles, so an ordinary admin is refused there too.
        (UserRole.ADMIN, (UserRole.SUPER_ADMIN,), 404),
        (UserRole.SUPER_ADMIN, (UserRole.SUPER_ADMIN,), 200),
    ],
)
def test_role_guard(current_role, allowed, expected) -> None:
    response = _app_with_guard(*allowed, current_role=current_role).get("/guarded")
    assert response.status_code == expected


def test_insufficient_role_is_indistinguishable_from_a_missing_route() -> None:
    client = _app_with_guard(UserRole.ADMIN, current_role=UserRole.USER)
    refused = client.get("/guarded")
    missing = client.get("/no-such-path")
    assert refused.status_code == missing.status_code == 404
