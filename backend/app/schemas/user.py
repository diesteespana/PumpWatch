import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import PASSWORD_MIN_LENGTH
from app.models.user import SubscriptionTier


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    is_verified: bool
    subscription_tier: SubscriptionTier
    created_at: datetime


class UserPublic(BaseModel):
    """Minimal public profile — safe to expose in shared contexts."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    subscription_tier: SubscriptionTier
