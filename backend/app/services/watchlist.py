"""Watchlist service layer -- CRUD operations with market data source sync.

Business logic for the watchlist API endpoints. Adding a ticker persists it
to the DB AND registers it with the market data source so prices start
streaming. Removing does the reverse.
"""

from __future__ import annotations

from asyncpg import Pool

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def get_watchlist(pool: Pool, price_cache: PriceCache) -> list[dict]:
    """Get all watched tickers enriched with live price data.

    Returns a list of dicts matching WatchlistItem shape.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = $1 ORDER BY added_at",
            DEFAULT_USER_ID,
        )

    result = []
    for row in rows:
        ticker = row["ticker"]
        update = price_cache.get(ticker)
        added_at = row["added_at"]

        item = {
            "ticker": ticker,
            "current_price": update.price if update else None,
            "change": update.change if update else None,
            "change_percent": update.change_percent if update else None,
            "direction": update.direction if update else None,
            "added_at": added_at.isoformat() if added_at else None,
        }
        result.append(item)

    return result


async def add_ticker(pool: Pool, source: MarketDataSource, ticker: str) -> None:
    """Add a ticker to the watchlist and register with market data source.

    Raises ValueError if ticker is already in the watchlist.
    """
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "INSERT INTO watchlist (user_id, ticker) VALUES ($1, $2) "
            "ON CONFLICT (user_id, ticker) DO NOTHING RETURNING id",
            DEFAULT_USER_ID,
            ticker,
        )

    if result is None:
        raise ValueError(f"{ticker} already in watchlist")

    # Register with market data source so prices start streaming (WATCH-04)
    await source.add_ticker(ticker)


async def remove_ticker(pool: Pool, source: MarketDataSource, ticker: str) -> None:
    """Remove a ticker from the watchlist and unregister from market data source.

    Raises ValueError if ticker is not in the watchlist.
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM watchlist WHERE user_id = $1 AND ticker = $2",
            DEFAULT_USER_ID,
            ticker,
        )

    # asyncpg returns status string like "DELETE 0" or "DELETE 1"
    if result == "DELETE 0":
        raise ValueError(f"{ticker} not in watchlist")

    # Unregister from market data source (WATCH-05)
    await source.remove_ticker(ticker)
