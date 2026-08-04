from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RiskProfileUpsert(BaseModel):
    stop_loss_pct: Decimal = Field(default=Decimal("10"), ge=1, le=99)
    take_profit_pct: Decimal = Field(default=Decimal("50"), ge=1, le=10000)
    max_position_pct: Decimal = Field(default=Decimal("25"), ge=1, le=100)
    max_drawdown_pct: Decimal = Field(default=Decimal("30"), ge=1, le=99)


class RiskProfileResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    max_position_pct: Decimal
    max_drawdown_pct: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    token_contract: str = Field(..., min_length=42, max_length=42)
    token_symbol: str = Field(..., min_length=1, max_length=20)
    chain: str = Field(default="ethereum", min_length=1, max_length=30)
    signal_direction: str = Field(..., pattern="^(bullish|bearish|any)$")
    min_confidence: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)
    action: str = Field(..., pattern="^(buy|sell)$")
    size_pct: Decimal = Field(default=Decimal("10"), ge=1, le=100)

    @field_validator("token_symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

    @field_validator("token_contract")
    @classmethod
    def lowercase_contract(cls, v: str) -> str:
        return v.lower()


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    signal_direction: str | None = Field(default=None, pattern="^(bullish|bearish|any)$")
    min_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    action: str | None = Field(default=None, pattern="^(buy|sell)$")
    size_pct: Decimal | None = Field(default=None, ge=1, le=100)


class StrategyResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    token_contract: str
    token_symbol: str
    chain: str
    signal_direction: str
    min_confidence: Decimal
    action: str
    size_pct: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyRunResponse(BaseModel):
    id: uuid.UUID
    strategy_id: uuid.UUID
    triggered: bool
    signal_direction: str | None
    signal_confidence: Decimal | None
    trade_id: uuid.UUID | None
    reason: str | None
    evaluated_at: datetime

    model_config = {"from_attributes": True}
