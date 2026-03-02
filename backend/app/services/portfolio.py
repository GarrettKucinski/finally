"""Portfolio service layer -- trade execution, portfolio query, snapshot recording.

Stub for TDD RED phase. All functions raise NotImplementedError.
"""

from __future__ import annotations


DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def execute_trade(pool, price_cache, ticker: str, side: str, quantity: float) -> dict:
    """Execute a trade atomically. Returns trade details or raises ValueError."""
    raise NotImplementedError("Not yet implemented")


async def get_portfolio(pool, price_cache) -> dict:
    """Get current portfolio state enriched with live prices."""
    raise NotImplementedError("Not yet implemented")


async def record_snapshot(pool, price_cache) -> None:
    """Record a portfolio value snapshot."""
    raise NotImplementedError("Not yet implemented")
