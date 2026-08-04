"""Unit tests for Pydantic schema validation."""
import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate
from app.schemas.wallet import TrackWalletRequest


def test_user_create_valid():
    user = UserCreate(email="Test@Example.COM", username="alice123", password="securepass")
    assert user.email == "test@example.com"


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", username="alice", password="securepass")


def test_user_create_short_password():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", username="alice", password="short")


def test_user_create_invalid_username_chars():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", username="alice!@#", password="securepass1")


def test_track_wallet_normalises_address():
    req = TrackWalletRequest(
        address="0x3F5CE5FBFE3E9AF3971DD833D26BA9B5C936F0BE"
    )
    assert req.address == "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"


def test_track_wallet_rejects_invalid_address():
    with pytest.raises(ValidationError):
        TrackWalletRequest(address="not-an-address")


def test_track_wallet_rejects_short_address():
    with pytest.raises(ValidationError):
        TrackWalletRequest(address="0x1234")
