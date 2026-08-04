import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.ethereum import is_valid_address, normalize_address


class TrackTokenRequest(BaseModel):
    contract_address: str
    chain: str = "ethereum"
    symbol: str = Field(max_length=20)
    name: str = Field(default="", max_length=100)
    threshold_usd: float | None = Field(default=None, gt=0)

    @field_validator("contract_address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        normalised = normalize_address(v)
        if not is_valid_address(normalised):
            raise ValueError(f"Invalid contract address: {v}")
        return normalised

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str) -> str:
        return v.upper()


class TokenResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    contract_address: str
    chain: str
    symbol: str
    name: str | None
    threshold_usd: float | None = None
    created_at: datetime
