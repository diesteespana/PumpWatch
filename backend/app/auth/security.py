"""
Password hashing and JWT creation / verification.

JWT strategy:
  Access token:  short-lived (30 min), payload {"sub": user_id, "type": "access"}
  Refresh token: long-lived (30 days), payload {"sub": user_id, "type": "refresh", "jti": uuid}

Refresh tokens are stored in Redis keyed by jti.  On each /auth/refresh the old
jti is deleted and a new pair is issued (rotation).  On logout the jti is deleted.
This allows instant invalidation without a DB write on every request.
"""
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import ExpiredTokenError, InvalidTokenError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


# ── Password ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────

def _settings():
    return get_settings()


def create_access_token(user_id: str) -> str:
    s = _settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=s.jwt_access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "type": _ACCESS_TYPE, "exp": expire},
        s.jwt_secret_key,
        algorithm=s.jwt_algorithm,
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Return (encoded_token, jti).  Caller stores jti in Redis."""
    s = _settings()
    jti = str(uuid.uuid4())
    expire = datetime.now(tz=timezone.utc) + timedelta(days=s.jwt_refresh_token_expire_days)
    token = jwt.encode(
        {"sub": user_id, "type": _REFRESH_TYPE, "jti": jti, "exp": expire},
        s.jwt_secret_key,
        algorithm=s.jwt_algorithm,
    )
    return token, jti


def decode_access_token(token: str) -> str:
    """Return user_id string.  Raises InvalidTokenError / ExpiredTokenError."""
    return _decode(token, expected_type=_ACCESS_TYPE)


def decode_refresh_token(token: str) -> tuple[str, str]:
    """Return (user_id, jti).  Raises on invalid / expired."""
    s = _settings()
    try:
        payload = jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        _raise_jwt_error(exc)
    if payload.get("type") != _REFRESH_TYPE:
        raise InvalidTokenError("Not a refresh token")
    return payload["sub"], payload["jti"]


def _decode(token: str, expected_type: str) -> str:
    s = _settings()
    try:
        payload = jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        _raise_jwt_error(exc)
    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected token type '{expected_type}'")
    return payload["sub"]


def _raise_jwt_error(exc: JWTError) -> None:
    if "expired" in str(exc).lower():
        raise ExpiredTokenError("Token has expired") from exc
    raise InvalidTokenError("Invalid token") from exc
