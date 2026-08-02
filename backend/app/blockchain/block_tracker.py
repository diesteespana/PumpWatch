"""
Block position tracker backed by Redis.

Tracks the last successfully processed block per chain so that after a
restart or crash we resume exactly where we left off — no gaps, no re-processing.

Redis is chosen over the DB here because:
- It is updated on every poll cycle (high write frequency)
- Loss of this value is low-cost (we fall back to current_block - LOOKBACK)
- DB writes would create unnecessary contention with event storage
"""
import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)

_KEY_TEMPLATE = "pumpwatch:block_tracker:{chain}"
_LOOKBACK_BLOCKS = 50  # safe default on first run or after Redis flush


class BlockTracker:
    """Persists and retrieves the last processed block number per chain."""

    def __init__(self, redis_client: aioredis.Redis, chain: str) -> None:
        self._redis = redis_client
        self._chain = chain
        self._key = _KEY_TEMPLATE.format(chain=chain)

    async def get_last_processed_block(self, current_block: int) -> int:
        """
        Return the block to start processing from.

        On first run (no Redis key) returns current_block - LOOKBACK
        so we immediately have some history without scanning the whole chain.
        """
        stored = await self._redis.get(self._key)
        if stored is None:
            fallback = max(0, current_block - _LOOKBACK_BLOCKS)
            logger.info(
                "block_tracker_cold_start",
                chain=self._chain,
                fallback_block=fallback,
            )
            return fallback
        return int(stored)

    async def set_last_processed_block(self, block_number: int) -> None:
        """Persist the latest successfully processed block."""
        await self._redis.set(self._key, str(block_number))
        logger.debug(
            "block_tracker_updated", chain=self._chain, block=block_number
        )

    async def reset(self) -> None:
        """Force a re-scan from the lookback window. Useful for manual recovery."""
        await self._redis.delete(self._key)
        logger.warning("block_tracker_reset", chain=self._chain)
