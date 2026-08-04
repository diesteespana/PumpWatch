"""
FastAPI auth dependencies.

get_current_user:      requires a valid access token, returns the User ORM object.
get_current_active_user: additionally checks is_active.
get_superuser:         additionally checks is_superuser.

All three are used via FastAPI Depends() in router handlers.
"""
import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing authorization header")

    user_id_str = decode_access_token(credentials.credentials)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Malformed token subject")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise AuthorizationError("Account is deactivated")
    return user


async def get_superuser(
    user: User = Depends(get_current_active_user),
) -> User:
    if not user.is_superuser:
        raise AuthorizationError("Superuser access required")
    return user
