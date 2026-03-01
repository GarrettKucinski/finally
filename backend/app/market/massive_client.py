"""
MassiveDataSource — REST-polling market data source backed by Massive (Polygon.io).

Polls the snapshot endpoint for all watched tickers in a single API call
and writes results to the PriceCache. The poll interval defaults to 15 seconds
(safe for the free tier: 5 req/min).

The Massive RESTClient is synchronous, so all API calls run via
asyncio.to_thread() to avoid blocking the event loop. This is why PriceCache
uses a threading.Lock.
"""

from __future__ import annotations

import asyncio
import logging

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """Market data source that polls the Massive (Polygon.io) REST API.

    Uses the v2 snapshot endpoint to fetch current prices for all watchlist
    tickers in a single API call — critical for staying within free-tier
    rate limits (5 req/min).

    Args:
        api_key: Massive API key (MASSIVE_API_KEY env var)
        price_cache: Shared PriceCache to write price updates into
        poll_interval: Seconds between API polls (default: 15s for free tier)
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client = None  # Set during start(); type: RESTClient

    async def start(self, tickers: list[str]) -> None:
        """Initialize the REST client and begin polling.

        Performs an immediate first poll so the cache has data right away,
        then launches the background polling loop.
        """
        from massive import RESTClient

        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Immediate first poll so cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")

    async def stop(self) -> None:
        """Cancel the polling task. Safe to call multiple times."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None

    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the watched set. Will appear on the next poll."""
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the watched set and clear it from the cache."""
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        """Return a copy of the current ticker list."""
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        """Poll on a fixed interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots and update the cache.

        Runs the synchronous REST client in a thread pool to avoid blocking
        the asyncio event loop. Errors are caught and logged — the loop
        always continues.
        """
        if not self._tickers or not self._client:
            return

        try:
            # The Massive RESTClient is synchronous — run in a thread
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    # Massive timestamps are Unix milliseconds → convert to seconds
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=snap.ticker,
                        price=price,
                        timestamp=timestamp,
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping malformed snapshot for %s: %s",
                        getattr(snap, "ticker", "???"),
                        e,
                    )
        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — the loop will retry on the next interval

    def _fetch_snapshots(self) -> list:
        """Synchronous call to the Massive REST API. Runs in a thread.

        Fetches current snapshot data for all watched tickers in a single
        API call using the v2 snapshot endpoint.
        """
        from massive.rest.models import SnapshotMarketType

        return list(
            self._client.get_snapshot_all(
                market_type=SnapshotMarketType.STOCKS,
                tickers=self._tickers,
            )
        )
