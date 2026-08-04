"""Unit tests for password hashing and JWT functions."""
import time

import pytest
from jose import jwt

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import ExpiredTokenError, InvalidTokenError


# ── Password ──────────────────────────────────────────────────────────────────

def test_hash_and_verify():
    plain = "supersecret123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_fails():
    assert not verify_password("wrong", hash_password("correct"))


def test_hashes_are_unique():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt salts


# ── Access token ──────────────────────────────────────────────────────────────

def test_access_token_round_trip():
    user_id = "abc123"
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_access_token_wrong_type_rejected():
    token, _ = create_refresh_token("user1")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_invalid_access_token_raises():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.jwt")


# ── Refresh token ─────────────────────────────────────────────────────────────

def test_refresh_token_round_trip():
    user_id = "user-xyz"
    token, jti = create_refresh_token(user_id)
    decoded_user, decoded_jti = decode_refresh_token(token)
    assert decoded_user == user_id
    assert decoded_jti == jti


def test_refresh_token_unique_jti():
    _, jti1 = create_refresh_token("u1")
    _, jti2 = create_refresh_token("u1")
    assert jti1 != jti2


def test_access_token_rejected_as_refresh():
    token = create_access_token("user1")
    with pytest.raises(InvalidTokenError):
        decode_refresh_token(token)
