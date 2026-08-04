"""
Large swap and liquidity classifiers.

LargeSwap:        transfer routed through a known DEX above the swap threshold.
LiquidityAdded:   transfer TO a DEX pool with LP-token-like characteristics.
LiquidityRemoved: transfer FROM a DEX pool.

LP token heuristics used here are intentionally conservative (0.70 confidence)
because distinguishing a swap from a liquidity provision purely from transfer
data requires additional context (e.g., checking for paired transfers in the
same tx). Full LP detection via event logs comes in Milestone 8.
"""
from app.blockchain.address_registry import AddressCategory
from app.blockchain.chain_service import EnrichedTransfer
from app.events.interfaces import EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType

# Common LP token symbols — rough heuristic until we decode event logs
_LP_SYMBOLS = frozenset({"UNI-V2", "SLP", "CAKE-LP", "CURVE", "BPT", "aToken"})


def _is_dex(transfer: EnrichedTransfer, side: str) -> bool:
    label = transfer.to_label if side == "to" else transfer.from_label
    return label is not None and label.category == AddressCategory.EXCHANGE_DEX


class LargeSwapClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.large_swap_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.LARGE_SWAP

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        if not (_is_dex(transfer, "to") or _is_dex(transfer, "from")):
            return None

        dex_name = (
            (transfer.to_label.name if transfer.to_label else None)
            or (transfer.from_label.name if transfer.from_label else "DEX")
        )
        return BaseEvent(
            event_type=EventType.LARGE_SWAP,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=0.85,
            explanation=(
                f"Large swap of ${usd:,.0f} in {transfer.token_symbol} "
                f"via {dex_name}."
            ),
            raw_value=transfer.token_amount,
            metadata={"dex": dex_name},
        )


class LiquidityAddedClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.liquidity_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.LIQUIDITY_ADDED

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        if not _is_dex(transfer, "to"):
            return None
        if transfer.token_symbol.upper() in _LP_SYMBOLS:
            return None  # receiving LP tokens = the paired tx; don't double-count

        dex_name = transfer.to_label.name if transfer.to_label else "DEX"
        return BaseEvent(
            event_type=EventType.LIQUIDITY_ADDED,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=0.70,
            explanation=(
                f"Potential liquidity provision of ${usd:,.0f} in "
                f"{transfer.token_symbol} to {dex_name}."
            ),
            raw_value=transfer.token_amount,
            metadata={"dex": dex_name},
        )


class LiquidityRemovedClassifier(EventClassifier):
    def __init__(self, config: ThresholdConfig) -> None:
        self._threshold = config.liquidity_threshold_usd

    @property
    def event_type(self) -> str:
        return EventType.LIQUIDITY_REMOVED

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        if not _is_dex(transfer, "from"):
            return None
        if transfer.token_symbol.upper() in _LP_SYMBOLS:
            return None

        dex_name = transfer.from_label.name if transfer.from_label else "DEX"
        return BaseEvent(
            event_type=EventType.LIQUIDITY_REMOVED,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.to_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=0.70,
            explanation=(
                f"Potential liquidity removal of ${usd:,.0f} in "
                f"{transfer.token_symbol} from {dex_name}."
            ),
            raw_value=transfer.token_amount,
            metadata={"dex": dex_name},
        )
