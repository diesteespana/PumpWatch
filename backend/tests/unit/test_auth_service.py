"""Unit tests for AuthService — mocked repo + Redis."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.security import hash_password
from app.auth.service import AuthService
from app.core.exceptions import AuthenticationError, ConflictError, InvalidTokenError


def make_user(is_active: bool = True):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "alice@example.com"
    u.hashed_password = hash_password("password123")
    u.is_active = is_active
    return u


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.setex = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.delete = AsyncMock()
    return r


@pytest.fixture
def mock_repo():
    r = AsyncMock()
    r.email_exists = AsyncMock(return_value=False)
    r.username_exists = AsyncMock(return_value=False)
    r.create = AsyncMock(return_value=make_user())
    r.get_by_email = AsyncMock(return_value=make_user())
    return r


@pytest.fixture
def svc(mock_repo, mock_redis):
    return AuthService(user_repo=mock_repo, redis_client=mock_redis)


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(svc, mock_repo):
    user = await svc.register("alice@example.com", "alice", "password123")
    mock_repo.create.assert_called_once()
    assert user is not None


@pytest.mark.asyncio
async def test_register_duplicate_email(svc, mock_repo):
    mock_repo.email_exists = AsyncMock(return_value=True)
    with pytest.raises(ConflictError):
        await svc.register("alice@example.com", "alice", "password123")


@pytest.mark.asyncio
async def test_register_duplicate_username(svc, mock_repo):
    mock_repo.username_exists = AsyncMock(return_value=True)
    with pytest.raises(ConflictError):
        await svc.register("new@example.com", "alice", "password123")


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(svc, mock_redis):
    access, refresh = await svc.login("alice@example.com", "password123")
    assert access
    assert refresh
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_login_wrong_password(svc):
    with pytest.raises(AuthenticationError):
        await svc.login("alice@example.com", "wrong")


@pytest.mark.asyncio
async def test_login_user_not_found(svc, mock_repo):
    mock_repo.get_by_email = AsyncMock(return_value=None)
    with pytest.raises(AuthenticationError):
        await svc.login("nobody@example.com", "password123")


@pytest.mark.asyncio
async def test_login_inactive_user(svc, mock_repo):
    mock_repo.get_by_email = AsyncMock(return_value=make_user(is_active=False))
    with pytest.raises(AuthenticationError):
        await svc.login("alice@example.com", "password123")


# ── Refresh ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_valid_token(svc, mock_redis):
    _, refresh = await svc.login("alice@example.com", "password123")
    user_id = str(make_user().id)
    mock_redis.get = AsyncMock(return_value=user_id)

    # patch decode to return consistent user_id
    from app.auth import service as svc_module
    from unittest.mock import patch
    with patch.object(svc_module, "decode_refresh_token", return_value=(user_id, "jti-abc")):
        mock_redis.get = AsyncMock(return_value=user_id)
        access, new_refresh = await svc.refresh(refresh)
    assert access
    assert new_refresh


@pytest.mark.asyncio
async def test_refresh_revoked_token(svc, mock_redis):
    from unittest.mock import patch
    from app.auth import service as svc_module
    with patch.object(svc_module, "decode_refresh_token", return_value=("uid", "jti")):
        mock_redis.get = AsyncMock(return_value=None)  # not in Redis = revoked
        with pytest.raises(InvalidTokenError):
            await svc.refresh("any-token")


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_deletes_jti(svc, mock_redis):
    from unittest.mock import patch
    from app.auth import service as svc_module
    with patch.object(svc_module, "decode_refresh_token", return_value=("uid", "jti-xyz")):
        await svc.logout("any-token")
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_logout_bad_token_does_not_raise(svc):
    await svc.logout("invalid-token")  # must not raise
