"""
APScheduler configuration for PumpWatch background jobs.

Design decisions:
- AsyncIOScheduler: shares the event loop with FastAPI — no thread overhead
- `misfire_grace_time`: if a cycle is still running when the next fires,
  wait up to 30s before skipping — avoids duplicate processing
- `max_instances=1`: guarantee only one poll cycle runs at a time per chain
- Jobs are registered at startup, not at import time, so tests can skip them
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance (created on first call)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            job_defaults={
                "misfire_grace_time": 30,
                "coalesce": True,
                "max_instances": 1,
            }
        )
    return _scheduler


async def start_scheduler() -> None:
    """Start the scheduler and register all background jobs."""
    settings = get_settings()
    scheduler = get_scheduler()

    # Lazy import to avoid circular deps during tests
    from app.blockchain.address_registry import AddressRegistry
    from app.blockchain.block_tracker import BlockTracker
    from app.blockchain.chain_service import EthereumChainService
    from app.blockchain.factory import create_blockchain_provider
    from app.blockchain.price_oracle import CoinGeckoPriceOracle
    from app.database.redis import get_redis_client

    redis_client = get_redis_client()
    provider = create_blockchain_provider()
    price_oracle = CoinGeckoPriceOracle(redis_client=redis_client)
    block_tracker = BlockTracker(redis_client=redis_client, chain="ethereum")
    address_registry = AddressRegistry()

    chain_service = EthereumChainService(
        provider=provider,
        price_oracle=price_oracle,
        block_tracker=block_tracker,
        address_registry=address_registry,
    )

    async def poll_ethereum() -> None:
        # Milestone 3 will pull watched_addresses from the DB.
        # For now we seed a handful of high-volume addresses for dev/demo.
        demo_addresses: list[str] = []
        transfers = await chain_service.poll_cycle(demo_addresses)
        if transfers:
            logger.info("scheduler_poll_complete", transfers=len(transfers))

    scheduler.add_job(
        poll_ethereum,
        trigger=IntervalTrigger(seconds=settings.blockchain_poll_interval_seconds),
        id="ethereum_poll",
        name="Ethereum block poller",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "scheduler_started",
        interval_seconds=settings.blockchain_poll_interval_seconds,
    )


async def stop_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
