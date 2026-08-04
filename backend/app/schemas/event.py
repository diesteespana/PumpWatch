import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.events.types import EventType


class OnChainEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    event_type: EventType
    blockchain: str
    tx_hash: str
    block_number: int
    timestamp: datetime
    wallet_address: str
    token_symbol: str
    token_contract: str
    usd_value: Decimal
    confidence_score: float
    explanation: str


class EventFilterParams(BaseModel):
    chain: str | None = None
    event_type: EventType | None = None
    wallet_address: str | None = None
    token_contract: str | None = None
    min_usd_value: float | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
