"""
Token mint and burn classifiers.

Mint:  ERC-20 transfer FROM the zero address → new tokens created.
Burn:  ERC-20 transfer TO the zero address → tokens destroyed.

Both are deterministic on-chain facts, so confidence is 1.0.
The threshold guard keeps noise out — tiny mints/burns are skipped.
"""
from app.blockchain.chain_service import EnrichedTransfer
from app.core.constants import ZERO_ADDRESS
from app.events.interfaces import EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType
from app.utils.ethereum import is_zero_address


class TokenMintClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.TOKEN_MINT

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        if not is_zero_address(transfer.from_address):
            return None
        if float(transfer.usd_value) < self._threshold:
            return None

        return BaseEvent(
            event_type=EventType.TOKEN_MINT,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.to_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=1.0,
            explanation=(
                f"{float(transfer.token_amount):,.2f} {transfer.token_symbol} "
                f"minted (≈${float(transfer.usd_value):,.0f}) "
                f"to {transfer.to_address[:10]}…"
            ),
            raw_value=transfer.token_amount,
        )


class TokenBurnClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.whale_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.TOKEN_BURN

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        if not is_zero_address(transfer.to_address):
            return None
        if float(transfer.usd_value) < self._threshold:
            return None

        return BaseEvent(
            event_type=EventType.TOKEN_BURN,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=1.0,
            explanation=(
                f"{float(transfer.token_amount):,.2f} {transfer.token_symbol} "
                f"burned (≈${float(transfer.usd_value):,.0f}) "
                f"from {transfer.from_address[:10]}…"
            ),
            raw_value=transfer.token_amount,
        )
