"""
Wallet-level pattern classifiers.

SmartMoneyActivity:   wallet has a pre-computed high reputation score (Milestone 9
                      will populate WalletScore; this classifier reads it).
WalletAccumulation:   wallet receives the same token multiple times in one batch
                      above the threshold — a buying pattern.
WalletDistribution:   wallet sends the same token multiple times — a selling pattern.

Accumulation/Distribution are batch-level classifiers: they operate on the
full transfer list, not individual transfers. The engine calls them separately
via `classify_batch()`. This is a deliberate design split — single-tx and
batch classifiers don't share the same interface.

Full time-window analysis (e.g., "accumulated over 7 days") arrives in M8.
"""
from collections import defaultdict
from decimal import Decimal

from app.blockchain.chain_service import EnrichedTransfer
from app.events.interfaces import EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent, EventType


class SmartMoneyClassifier(EventClassifier):
    """
    Fires when a known high-reputation wallet makes a significant move.

    In M4: reputation score comes from WalletScore table (may be empty).
    In M9: the AI engine populates and updates scores continuously.
    """

    def __init__(self, config: ThresholdConfig, min_score: float = 0.75) -> None:
        self._threshold = config.whale_threshold_usd
        self._min_score = min_score
        self._score_cache: dict[str, float] = {}  # address → score; refreshed per cycle

    @property
    def event_type(self) -> str:
        return EventType.SMART_MONEY_ACTIVITY

    def load_scores(self, scores: dict[str, float]) -> None:
        """Called by the engine before each batch with fresh DB scores."""
        self._score_cache = scores

    def classify(self, transfer: EnrichedTransfer) -> BaseEvent | None:
        usd = float(transfer.usd_value)
        if usd < self._threshold:
            return None
        score = self._score_cache.get(transfer.from_address, 0.0)
        if score < self._min_score:
            return None

        return BaseEvent(
            event_type=EventType.SMART_MONEY_ACTIVITY,
            blockchain=transfer.chain,
            tx_hash=transfer.tx_hash,
            block_number=transfer.block_number,
            timestamp=transfer.timestamp,
            wallet_address=transfer.from_address,
            token_symbol=transfer.token_symbol,
            token_contract=transfer.token_contract,
            usd_value=transfer.usd_value,
            confidence_score=round(min(0.95, 0.60 + score * 0.35), 4),
            explanation=(
                f"High-reputation wallet (score {score:.2f}) moved "
                f"${usd:,.0f} of {transfer.token_symbol}."
            ),
            raw_value=transfer.token_amount,
            metadata={"wallet_score": score},
        )


class AccumulationDistributionClassifier:
    """
    Batch classifier: detects accumulation and distribution patterns.

    Not an EventClassifier subclass because it needs the full transfer list
    to identify the pattern across multiple transactions.
    """

    def __init__(self, config: ThresholdConfig) -> None:
        self._min_transfers = config.accumulation_min_transfers
        self._threshold = config.whale_threshold_usd

    def classify_batch(self, transfers: list[EnrichedTransfer]) -> list[BaseEvent]:
        events: list[BaseEvent] = []

        # Group transfers by wallet address and token
        inbound: dict[tuple[str, str], list[EnrichedTransfer]] = defaultdict(list)
        outbound: dict[tuple[str, str], list[EnrichedTransfer]] = defaultdict(list)

        for t in transfers:
            usd = float(t.usd_value)
            if usd < self._threshold:
                continue
            key = (t.to_address, t.token_contract)
            inbound[key].append(t)
            out_key = (t.from_address, t.token_contract)
            outbound[out_key].append(t)

        # Accumulation: same wallet received same token N+ times above threshold
        for (wallet, contract), txs in inbound.items():
            if len(txs) >= self._min_transfers:
                total_usd = sum(float(t.usd_value) for t in txs)
                total_tokens = sum(t.token_amount for t in txs)
                symbol = txs[0].token_symbol
                latest = max(txs, key=lambda t: t.block_number)
                events.append(
                    BaseEvent(
                        event_type=EventType.WALLET_ACCUMULATION,
                        blockchain=txs[0].chain,
                        tx_hash=latest.tx_hash,
                        block_number=latest.block_number,
                        timestamp=latest.timestamp,
                        wallet_address=wallet,
                        token_symbol=symbol,
                        token_contract=contract,
                        usd_value=Decimal(str(total_usd)),
                        confidence_score=0.75,
                        explanation=(
                            f"Wallet {wallet[:10]}… accumulated {symbol} "
                            f"across {len(txs)} transactions "
                            f"totalling ${total_usd:,.0f}."
                        ),
                        raw_value=total_tokens,
                        metadata={"tx_count": len(txs), "total_usd": total_usd},
                    )
                )

        # Distribution: same wallet sent same token N+ times above threshold
        for (wallet, contract), txs in outbound.items():
            if len(txs) >= self._min_transfers:
                total_usd = sum(float(t.usd_value) for t in txs)
                total_tokens = sum(t.token_amount for t in txs)
                symbol = txs[0].token_symbol
                latest = max(txs, key=lambda t: t.block_number)
                events.append(
                    BaseEvent(
                        event_type=EventType.WALLET_DISTRIBUTION,
                        blockchain=txs[0].chain,
                        tx_hash=latest.tx_hash,
                        block_number=latest.block_number,
                        timestamp=latest.timestamp,
                        wallet_address=wallet,
                        token_symbol=symbol,
                        token_contract=contract,
                        usd_value=Decimal(str(total_usd)),
                        confidence_score=0.75,
                        explanation=(
                            f"Wallet {wallet[:10]}… distributed {symbol} "
                            f"across {len(txs)} transactions "
                            f"totalling ${total_usd:,.0f}."
                        ),
                        raw_value=total_tokens,
                        metadata={"tx_count": len(txs), "total_usd": total_usd},
                    )
                )

        return events
