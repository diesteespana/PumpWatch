"""
AuthService — all authentication business logic.

Refresh token storage in Redis:
  key: pumpwatch:refresh:{jti}  value: user_id  TTL: refresh_expire_days * 86400
This allows O(1) revocation and avoids a DB write on every request path.
"""
import uuid
from datetime import timedelta

import redis.asyncio as aioredis

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_refresh_token,
)
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError, InvalidTokenError
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.user import UserRepository

logger = get_logger(__name__)

_REFRESH_KEY = "pumpwatch:refresh:{jti}"


class AuthService:
    def __init__(self, user_repo: UserRepository, redis_client: aioredis.Redis) -> None:
        self._users = user_repo
        self._redis = redis_client

    async def register(self, email: str, username: str, password: str) -> User:
        if await self._users.email_exists(email):
            raise ConflictError(f"Email already registered: {email}")
        if await self._users.username_exists(username):
            raise ConflictError(f"Username already taken: {username}")

        user = await self._users.create(
            email=email.lower(),
            username=username,
            hashed_password=hash_password(password),
        )
        logger.info("user_registered", user_id=str(user.id), email=email)
        return user

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Return (access_token, refresh_token)."""
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        return await self._issue_token_pair(str(user.id))

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate refresh token: invalidate old jti, issue new pair."""
        try:
            user_id, jti = decode_refresh_token(refresh_token)
        except Exception as exc:
            raise InvalidTokenError("Invalid refresh token") from exc

        key = _REFRESH_KEY.format(jti=jti)
        stored = await self._redis.get(key)
        if stored is None:
            raise InvalidTokenError("Refresh token revoked or expired")
        if stored != user_id:
            raise InvalidTokenError("Refresh token user mismatch")

        await self._redis.delete(key)
        logger.info("token_rotated", user_id=user_id)
        return await self._issue_token_pair(user_id)

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token so it can no longer be used."""
        try:
            _, jti = decode_refresh_token(refresh_token)
            await self._redis.delete(_REFRESH_KEY.format(jti=jti))
        except Exception:
            pass  # already expired or invalid — treat as logged out

    async def _issue_token_pair(self, user_id: str) -> tuple[str, str]:
        s = get_settings()
        access = create_access_token(user_id)
        refresh, jti = create_refresh_token(user_id)
        ttl = int(timedelta(days=s.jwt_refresh_token_expire_days).total_seconds())
        await self._redis.setex(_REFRESH_KEY.format(jti=jti), ttl, user_id)
        return access, refresh
