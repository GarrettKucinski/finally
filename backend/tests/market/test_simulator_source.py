"""
Integration tests for SimulatorDataSource — async wrapper around GBMSimulator.

10 tests covering:
- start() seeds the cache immediately
- _run_loop() updates cache on each tick
- add_ticker() seeds cache for the new ticker
- remove_ticker() clears both simulator and cache
- stop() cancels the background task cleanly
- get_tickers() reflects current state
"""

import asyncio

import pytest

from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def source(cache: PriceCache) -> SimulatorDataSource:
    return SimulatorDataSource(price_cache=cache, update_interval=0.05)


class TestSimulatorDataSourceStart:
    """start() behavior."""

    async def test_start_seeds_cache_immediately(self, source: SimulatorDataSource, cache: PriceCache):
        """After start(), the cache already has prices — no need to wait for a tick."""
        await source.start(["AAPL", "GOOGL"])
        await source.stop()

        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None

    async def test_start_creates_background_task(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL"])
        assert source._task is not None
        assert not source._task.done()
        await source.stop()

    async def test_start_with_empty_tickers(self, source: SimulatorDataSource, cache: PriceCache):
        """Empty watchlist — source starts but cache is empty."""
        await source.start([])
        await source.stop()
        assert len(cache) == 0


class TestSimulatorDataSourceRunLoop:
    """_run_loop() updates cache on each tick."""

    async def test_cache_updates_after_ticks(self, source: SimulatorDataSource, cache: PriceCache):
        """After a few ticks, cache version should have increased."""
        await source.start(["AAPL"])
        initial_version = cache.version
        await asyncio.sleep(0.2)  # Allow 4 ticks at 50ms interval
        await source.stop()
        assert cache.version > initial_version


class TestSimulatorDataSourceAddRemoveTicker:
    """add_ticker() and remove_ticker() behavior."""

    async def test_add_ticker_seeds_cache(self, source: SimulatorDataSource, cache: PriceCache):
        """Adding a ticker immediately seeds the cache with a price."""
        await source.start(["AAPL"])
        await source.add_ticker("GOOGL")
        await source.stop()
        assert cache.get("GOOGL") is not None

    async def test_add_ticker_included_in_get_tickers(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL"])
        await source.add_ticker("MSFT")
        tickers = source.get_tickers()
        await source.stop()
        assert "MSFT" in tickers

    async def test_remove_ticker_clears_cache(self, source: SimulatorDataSource, cache: PriceCache):
        """Removing a ticker clears it from the cache."""
        await source.start(["AAPL", "GOOGL"])
        await source.remove_ticker("GOOGL")
        await source.stop()
        assert cache.get("GOOGL") is None

    async def test_remove_ticker_not_in_get_tickers(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL", "GOOGL"])
        await source.remove_ticker("GOOGL")
        tickers = source.get_tickers()
        await source.stop()
        assert "GOOGL" not in tickers

    async def test_add_then_remove_ticker(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL"])
        await source.add_ticker("TSLA")
        assert cache.get("TSLA") is not None
        await source.remove_ticker("TSLA")
        assert cache.get("TSLA") is None
        await source.stop()


class TestSimulatorDataSourceStop:
    """stop() behavior."""

    async def test_stop_cancels_task(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL"])
        task = source._task
        await source.stop()
        assert task is not None
        assert task.done()

    async def test_stop_idempotent(self, source: SimulatorDataSource, cache: PriceCache):
        """Calling stop() twice should not raise."""
        await source.start(["AAPL"])
        await source.stop()
        await source.stop()  # Should not raise


class TestSimulatorDataSourceGetTickers:
    """get_tickers() reflects current state."""

    async def test_get_tickers_before_start(self, source: SimulatorDataSource):
        """Before start(), get_tickers() returns empty list."""
        assert source.get_tickers() == []

    async def test_get_tickers_after_start(self, source: SimulatorDataSource, cache: PriceCache):
        await source.start(["AAPL", "GOOGL"])
        tickers = source.get_tickers()
        await source.stop()
        assert set(tickers) == {"AAPL", "GOOGL"}
