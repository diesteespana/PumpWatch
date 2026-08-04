import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.events.types import EventType


class AlertCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    event_types: list[EventType] = Field(default_factory=list)
    wallet_addresses: list[str] = Field(default_factory=list)
    token_contracts: list[str] = Field(default_factory=list)
    min_usd_value: float = Field(default=0.0, ge=0)


class AlertUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    event_types: list[EventType] | None = None
    wallet_addresses: list[str] | None = None
    token_contracts: list[str] | None = None
    min_usd_value: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_active: bool
    event_types: list[str]
    wallet_addresses: list[str]
    token_contracts: list[str]
    min_usd_value: float
    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseModel):
    """Generic paginated wrapper — used across all list endpoints."""

    total: int
    page: int
    page_size: int
    has_next: bool
    items: list
