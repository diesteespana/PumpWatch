"""
Exchange deposit and withdrawal classifiers.

Deposit:  any transfer TO a known CEX address above the whale threshold.
Withdrawal: any transfer FROM a known CEX address above the threshold.

Exchange activity gets higher confidence (0.90) because address labels are
curated — we're certain the address belongs to the exchange, even if we
can't be certain of the user's intent.
"""
from app.blockchain.chain_service import EnrichedTransfer
from app.events.interfaces import EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType

_CONFIDENCE = 0.90


class ExchangeDepositClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.EXCHANGE_DEPOSIT

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        if float(transfer.usd_value) < self._threshold:
            return None
        if not transfer.to_label:
            return None
        if not transfer.to_label.category.value == "exchange_cex":
            return None

        exchange = transfer.to_label.name
        return BaseEvent(
            event_type=EventType.EXCHANGE_DEPOSIT,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=_CONFIDENCE,
            explanation=(
                f"${float(transfer.usd_value):,.0f} of {transfer.token_symbol} "
                f"deposited to {exchange} from {transfer.from_address[:10]}…"
            ),
            raw_value=transfer.token_amount,
            metadata={"exchange": exchange},
        )


class ExchangeWithdrawalClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.EXCHANGE_WITHDRAWAL

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        if float(transfer.usd_value) < self._threshold:
            return None
        if not transfer.from_label:
            return None
        if not transfer.from_label.category.value == "exchange_cex":
            return None

        exchange = transfer.from_label.name
        return BaseEvent(
            event_type=EventType.EXCHANGE_WITHDRAWAL,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.to_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=_CONFIDENCE,
            explanation=(
                f"${float(transfer.usd_value):,.0f} of {transfer.token_symbol} "
                f"withdrawn from {exchange} to {transfer.to_address[:10]}…"
            ),
            raw_value=transfer.token_amount,
            metadata={"exchange": exchange},
        )
