"""Background tasks for portfolio snapshot recording and cleanup.

snapshot_recorder_loop: Records total portfolio value every 30 seconds (PORT-08).
snapshot_cleanup_loop: Deletes snapshots older than 24 hours every 5 minutes (PORT-10).

Both tasks are launched via asyncio.create_task() in the FastAPI lifespan and
cancelled on shutdown. They handle errors gracefully (log + continue).
"""

from __future__ import annotations

import asyncio
import logging

from asyncpg import Pool

from app.market.cache import PriceCache
from app.services.portfolio import record_snapshot

logger = logging.getLogger(__name__)


async def snapshot_recorder_loop(pool: Pool, price_cache: PriceCache) -> None:
    """Record portfolio snapshot every 30 seconds. Runs until cancelled."""
    while True:
        try:
            await record_snapshot(pool, price_cache)
        except Exception:
            logger.exception("Failed to record portfolio snapshot")
        await asyncio.sleep(30)


async def snapshot_cleanup_loop(pool: Pool) -> None:
    """Delete portfolio snapshots older than 24 hours. Runs every 5 minutes."""
    while True:
        try:
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM portfolio_snapshots WHERE recorded_at < NOW() - INTERVAL '24 hours'"
                )
                logger.debug("Snapshot cleanup: %s", result)
        except Exception:
            logger.exception("Failed to clean up portfolio snapshots")
        await asyncio.sleep(300)
