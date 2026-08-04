from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    starting_balance: Decimal = Field(..., gt=0, le=Decimal("1_000_000_000"))


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    name: str
    starting_balance: Decimal
    current_cash: Decimal
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    token_symbol: str
    token_contract: str
    chain: str
    quantity: Decimal
    avg_entry_price: Decimal
    current_price: Decimal | None = None
    current_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None

    model_config = {"from_attributes": True}


class TradeRequest(BaseModel):
    trade_type: str = Field(..., pattern="^(buy|sell)$")
    token_symbol: str = Field(..., min_length=1, max_length=20)
    token_contract: str = Field(..., min_length=42, max_length=42)
    chain: str = Field(default="ethereum", min_length=1, max_length=30)
    quantity: Decimal = Field(..., gt=0)
    trigger: str = Field(default="manual", pattern="^(manual|signal)$")

    @field_validator("token_symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

    @field_validator("token_contract")
    @classmethod
    def lowercase_contract(cls, v: str) -> str:
        return v.lower()


class TradeResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    trade_type: str
    token_symbol: str
    token_contract: str
    chain: str
    quantity: Decimal
    price_at_execution: Decimal
    total_value: Decimal
    realized_pnl: Decimal | None
    trigger: str
    executed_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummaryResponse(BaseModel):
    portfolio: PortfolioResponse
    positions: list[PositionResponse]
    total_position_value: Decimal
    total_equity: Decimal
    total_return: Decimal
    total_return_pct: Decimal
    realized_pnl: Decimal
