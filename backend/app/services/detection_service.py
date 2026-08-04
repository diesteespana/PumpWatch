"""
DetectionService — the top-level coordinator called by the scheduler.

Ties together:
  ChainService → EnrichedTransfer list
  DetectionEngine → BaseEvent list (classified + persisted)
  NotificationService → deliver to users (Milestone 5)

This is the only place that knows about both layers; neither chain_service
nor the detection engine imports the other.
"""
from app.blockchain.chain_service import EthereumChainService
from app.core.logging import get_logger
from app.events.engine import DefaultDetectionEngine
from app.events.types import BaseEvent

logger = get_logger(__name__)


class DetectionService:
    def __init__(
        self,
        chain_service: EthereumChainService,
        detection_engine: DefaultDetectionEngine,
    ) -> None:
        self._chain = chain_service
        self._engine = detection_engine

    async def run_cycle(self, watched_addresses: list[str]) -> list[BaseEvent]:
        """
        Full pipeline: fetch → enrich → classify → persist → return.

        Returns the list of newly detected events so the scheduler can
        forward them to the notification engine (Milestone 5).
        Never raises — errors are logged and an empty list is returned.
        """
        try:
            transfers = await self._chain.poll_cycle(watched_addresses)
            if not transfers:
                return []
            events = await self._engine.process_transfers(transfers)
            logger.info(
                "detection_service_cycle",
                addresses=len(watched_addresses),
                transfers=len(transfers),
                events=len(events),
            )
            return events
        except Exception as exc:
            logger.error("detection_service_error", error=str(exc), exc_info=True)
            return []
