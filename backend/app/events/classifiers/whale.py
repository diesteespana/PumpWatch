"""
Whale buy / sell classifiers.

A transfer is a "whale buy" when:
  - USD value exceeds the whale threshold
  - The destination is NOT a known exchange (otherwise it's a deposit)
  - Token is flowing TO the watched wallet

A transfer is a "whale sell" when:
  - USD value exceeds the threshold
  - The source is NOT a known exchange
  - Token is flowing FROM the watched wallet

Confidence scales with how far above threshold the value is, capped at 0.95
to acknowledge we never have certainty about intent from a single tx.
"""
from decimal import Decimal

from app.blockchain.chain_service import EnrichedTransfer
from app.events.interfaces import EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType
from app.core.constants import ETHEREUM_CHAIN_NAME


def _confidence(usd_value: float, threshold: float) -> float:
    ratio = usd_value / threshold
    base = 0.70
    boost = min(0.25, (ratio - 1.0) * 0.05)
    return round(min(0.95, base + boost), 4)


class WhaleBuyClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.WHALE_BUY

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        if transfer.to_label and transfer.to_label.category.value.startswith("exchange"):
            return None  # that's an exchange deposit, handled by a different classifier

        confidence = _confidence(usd, self._threshold)
        label = transfer.from_label.name if transfer.from_label else transfer.from_address[:10]
        return BaseEvent(
            event_type=EventType.WHALE_BUY,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.to_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=confidence,
            explanation=(
                f"Large {transfer.token_symbol} purchase of "
                f"${usd:,.0f} received by {transfer.to_address[:10]}… "
                f"from {label}."
            ),
            raw_value=transfer.token_amount,
        )


class WhaleSellClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.WHALE_SELL

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        if transfer.from_label and transfer.from_label.category.value.startswith("exchange"):
            return None  # exchange withdrawal, different classifier

        confidence = _confidence(usd, self._threshold)
        dest = transfer.to_label.name if transfer.to_label else transfer.to_address[:10]
        return BaseEvent(
            event_type=EventType.WHALE_SELL,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=confidence,
            explanation=(
                f"Large {transfer.token_symbol} sale of "
                f"${usd:,.0f} sent from {transfer.from_address[:10]}… "
                f"to {dest}."
            ),
            raw_value=transfer.token_amount,
        )
