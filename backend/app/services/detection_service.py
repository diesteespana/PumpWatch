"""
DetectionService — top-level coordinator called by the scheduler.

Pipeline:
  ChainService.poll_cycle()       → list[EnrichedTransfer]
  DetectionEngine.process_transfers() → list[BaseEvent]  (classified + persisted)
  NotificationService.notify_all_matching() → deliver to users
"""
from app.blockchain.chain_service import EthereumChainService
from app.core.logging import get_logger
from app.events.engine import DefaultDetectionEngine
from app.events.types import BaseEvent
from app.notifications.service import DefaultNotificationService

logger = get_logger(__name__)


class DetectionService:
    def __init__(
        self,
        chain_service: EthereumChainService,
        detection_engine: DefaultDetectionEngine,
        notification_service: DefaultNotificationService | None = None,
    ) -> None:
        self._chain = chain_service
        self._engine = detection_engine
        self._notifier = notification_service

    async def run_cycle(self, watched_addresses: list[str]) -> list[BaseEvent]:
        """
        Full pipeline: fetch → enrich → classify → persist → notify.
        Never raises — errors are logged and an empty list is returned.
        """
        try:
            transfers = await self._chain.poll_cycle(watched_addresses)
            if not transfers:
                return []

            events = await self._engine.process_transfers(transfers)

            if events and self._notifier:
                for event in events:
                    await self._notifier.notify_all_matching(event)

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
