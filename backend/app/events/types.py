"""
PumpWatch event type system.

Every detectable on-chain event is a typed subclass of BaseEvent.
This gives the detection engine, notification engine, and future AI engine
a common, strongly-typed contract to work with.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class EventType(StrEnum):
    WHALE_BUY = "whale_buy"
    WHALE_SELL = "whale_sell"
    EXCHANGE_DEPOSIT = "exchange_deposit"
    EXCHANGE_WITHDRAWAL = "exchange_withdrawal"
    LIQUIDITY_ADDED = "liquidity_added"
    LIQUIDITY_REMOVED = "liquidity_removed"
    CONTRACT_DEPLOYMENT = "contract_deployment"
    TOKEN_MINT = "token_mint"
    TOKEN_BURN = "token_burn"
    LARGE_SWAP = "large_swap"
    SMART_MONEY_ACTIVITY = "smart_money_activity"
    WALLET_ACCUMULATION = "wallet_accumulation"
    WALLET_DISTRIBUTION = "wallet_distribution"


@dataclass(frozen=True)
class BaseEvent:
    """
    Canonical representation of a detected on-chain event.

    Every field is required so downstream consumers can rely on the schema.
    confidence_score: 0.0–1.0, how certain the classifier is.
    explanation: human-readable sentence for display and future LLM context.
    """

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
    raw_value: Decimal = field(default=Decimal(0))
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        from app.core.constants import MAX_CONFIDENCE_SCORE, MIN_CONFIDENCE_SCORE

        if not (MIN_CONFIDENCE_SCORE <= self.confidence_score <= MAX_CONFIDENCE_SCORE):
            raise ValueError(
                f"confidence_score must be between {MIN_CONFIDENCE_SCORE} and "
                f"{MAX_CONFIDENCE_SCORE}, got {self.confidence_score}"
            )
