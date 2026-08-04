import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.ethereum import is_valid_address, normalize_address


class WalletCreate(BaseModel):
    address: str
    chain: str = "ethereum"
    label: str = Field(default="", max_length=100)
    threshold_usd: float | None = Field(default=None, gt=0)

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        normalised = normalize_address(v)
        if not is_valid_address(normalised):
            raise ValueError(f"Invalid Ethereum address: {v}")
        return normalised


class WalletResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    address: str
    chain: str
    label: str
    is_exchange: bool
    exchange_name: str | None
    created_at: datetime


class TrackWalletRequest(BaseModel):
    address: str
    chain: str = "ethereum"
    custom_label: str | None = Field(default=None, max_length=100)
    threshold_usd: float | None = Field(default=None, gt=0)

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        normalised = normalize_address(v)
        if not is_valid_address(normalised):
            raise ValueError(f"Invalid Ethereum address: {v}")
        return normalised
