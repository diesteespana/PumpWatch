"""
DefaultDetectionEngine — the central orchestrator.

Responsibilities:
1. Run all single-tx EventClassifiers on each EnrichedTransfer
2. Run the batch AccumulationDistributionClassifier on the full list
3. Filter by minimum confidence threshold
4. Deduplicate against already-persisted events (tx_hash + event_type)
5. Persist new events via EventRepository
6. Return the full list for the notification engine

Classifiers are registered at construction time; adding a new event type
requires only writing a classifier and registering it here — zero changes
to the engine logic.
"""
from app.blockchain.chain_service import EnrichedTransfer
from app.core.logging import get_logger
from app.events.classifiers.contract import ContractDeploymentClassifier
from app.events.classifiers.exchange import (
    ExchangeDepositClassifier,
    ExchangeWithdrawalClassifier,
)
from app.events.classifiers.swap import (
    LargeSwapClassifier,
    LiquidityAddedClassifier,
    LiquidityRemovedClassifier,
)
from app.events.classifiers.token_ops import TokenBurnClassifier, TokenMintClassifier
from app.events.classifiers.wallet import (
    AccumulationDistributionClassifier,
    SmartMoneyClassifier,
)
from app.events.classifiers.whale import WhaleBuyClassifier, WhaleSellClassifier
from app.events.interfaces import DetectionEngine, EventClassifier
from app.events.threshold import ThresholdConfig
from app.events.types import BaseEvent
from app.repositories.event import EventRepository

logger = get_logger(__name__)


def build_default_classifiers(config: ThresholdConfig) -> list[EventClassifier]:
    """Return the full registered classifier list in priority order."""
    return [
        # Deterministic first — highest confidence, no threshold ambiguity
        ContractDeploymentClassifier(),
        TokenMintClassifier(config),
        TokenBurnClassifier(config),
        # Exchange-labelled — high confidence from curated address registry
        ExchangeDepositClassifier(config),
        ExchangeWithdrawalClassifier(config),
        # DEX interactions
        LargeSwapClassifier(config),
        LiquidityAddedClassifier(config),
        LiquidityRemovedClassifier(config),
        # Whale activity (after exchange classifiers so deposits don't double-fire)
        WhaleBuyClassifier(config),
        WhaleSellClassifier(config),
        # Smart money (requires score cache to be loaded first)
        SmartMoneyClassifier(config),
    ]


class DefaultDetectionEngine(DetectionEngine):
    def __init__(
        self,
        event_repo: EventRepository,
        config: ThresholdConfig | None = None,
        classifiers: list[EventClassifier] | None = None,
    ) -> None:
        self._config = config or ThresholdConfig.from_settings()
        self._classifiers = classifiers or build_default_classifiers(self._config)
        self._batch_classifier = AccumulationDistributionClassifier(self._config)
        self._event_repo = event_repo

    async def process_transfers(self, transfers: list[EnrichedTransfer]) -> list[BaseEvent]:
        if not transfers:
            return []

        raw_events: list[BaseEvent] = []

        # Single-tx classifiers
        for transfer in transfers:
            for classifier in self._classifiers:
                try:
                    event = classifier.classify(transfer)
                    if event is not None:
                        raw_events.append(event)
                except Exception as exc:
                    logger.error(
                        "classifier_error",
                        classifier=type(classifier).__name__,
                        tx=transfer.tx_hash,
                        error=str(exc),
                        exc_info=True,
                    )

        # Batch classifiers (accumulation / distribution)
        try:
            batch_events = self._batch_classifier.classify_batch(transfers)
            raw_events.extend(batch_events)
        except Exception as exc:
            logger.error("batch_classifier_error", error=str(exc), exc_info=True)

        # Filter by minimum confidence
        above_threshold = [
            e for e in raw_events
            if e.confidence_score >= self._config.min_confidence_to_persist
        ]

        # Deduplicate against DB
        new_events: list[BaseEvent] = []
        for event in above_threshold:
            already_stored = await self._event_repo.tx_hash_exists(
                event.tx_hash, event.event_type
            )
            if not already_stored:
                new_events.append(event)

        # Persist
        persisted: list[BaseEvent] = []
        for event in new_events:
            try:
                await self._event_repo.create(
                    event_type=event.event_type,
                    blockchain=event.blockchain,
                    tx_hash=event.tx_hash,
                    block_number=event.block_number,
                    timestamp=event.timestamp,
                    wallet_address=event.wallet_address,
                    token_symbol=event.token_symbol,
                    token_contract=event.token_contract,
                    usd_value=float(event.usd_value),
                    confidence_score=event.confidence_score,
                    explanation=event.explanation,
                    raw_metadata=event.metadata,
                )
                persisted.append(event)
            except Exception as exc:
                logger.error(
                    "event_persist_error",
                    tx=event.tx_hash,
                    event_type=event.event_type,
                    error=str(exc),
                    exc_info=True,
                )

        logger.info(
            "detection_cycle_complete",
            transfers=len(transfers),
            raw_detected=len(raw_events),
            new_persisted=len(persisted),
        )
        return persisted

    async def run_cycle(self) -> int:
        # Wired by the scheduler service; left abstract here
        # because the engine itself doesn't own the chain service.
        raise NotImplementedError("Use DetectionService.run_cycle() via the scheduler.")
