"""
Tests for app.market.massive_client — MassiveDataSource.

13 tests covering:
- _poll_once() updates cache with correct prices
- Timestamp conversion from milliseconds to seconds
- Malformed snapshots are skipped (not crashed)
- API errors are caught and logged
- add_ticker() normalizes to uppercase
- remove_ticker() clears from list and cache
- stop() cancels task and clears client
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


@pytest.fixture
def source(cache: PriceCache) -> MassiveDataSource:
    return MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)


def make_mock_snapshot(ticker: str, price: float, timestamp_ms: float) -> MagicMock:
    """Create a mock snapshot object resembling the Massive API response."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap


class TestMassiveDataSourcePollOnce:
    """_poll_once() correctly updates the PriceCache."""

    async def test_poll_updates_cache(self, source: MassiveDataSource, cache: PriceCache):
        snapshots = [
            make_mock_snapshot("AAPL", 191.50, 1709312400000.0),
            make_mock_snapshot("GOOGL", 175.25, 1709312400000.0),
        ]
        source._client = MagicMock()
        with patch.object(source, "_fetch_snapshots", return_value=snapshots):
            await source._poll_once()

        assert cache.get_price("AAPL") == 191.50
        assert cache.get_price("GOOGL") == 175.25

    async def test_poll_timestamp_conversion(self, source: MassiveDataSource, cache: PriceCache):
        """Timestamps from Massive are in milliseconds; should be converted to seconds."""
        timestamp_ms = 1709312400000.0  # 1709312400.0 in seconds
        snapshots = [make_mock_snapshot("AAPL", 191.50, timestamp_ms)]
        source._client = MagicMock()
        with patch.object(source, "_fetch_snapshots", return_value=snapshots):
            await source._poll_once()

        update = cache.get("AAPL")
        assert update is not None
        assert abs(update.timestamp - 1709312400.0) < 0.001

    async def test_poll_skips_empty_ticker_list(self, source: MassiveDataSource, cache: PriceCache):
        """No API call made if there are no tickers."""
        source._client = MagicMock()
        source._tickers = []
        with patch.object(source, "_fetch_snapshots") as mock_fetch:
            await source._poll_once()
        mock_fetch.assert_not_called()

    async def test_poll_skips_malformed_snapshot(self, source: MassiveDataSource, cache: PriceCache):
        """Malformed snapshots are skipped; others are still processed."""
        bad_snap = MagicMock()
        bad_snap.ticker = "BAD"
        bad_snap.last_trade.price = None  # Will cause TypeError in cache.update
        good_snap = make_mock_snapshot("AAPL", 191.00, 1709312400000.0)

        source._client = MagicMock()
        source._tickers = ["BAD", "AAPL"]

        # Make the bad snap raise AttributeError when accessing last_trade.price
        bad_snap.last_trade = None  # type: ignore[assignment]

        with patch.object(source, "_fetch_snapshots", return_value=[bad_snap, good_snap]):
            await source._poll_once()  # Should not raise

        # Good snapshot should still be processed
        assert cache.get_price("AAPL") == 191.00

    async def test_poll_handles_api_error(self, source: MassiveDataSource, cache: PriceCache):
        """API errors are caught and logged — the source never crashes."""
        source._client = MagicMock()
        source._tickers = ["AAPL"]
        with patch.object(source, "_fetch_snapshots", side_effect=Exception("API error")):
            await source._poll_once()  # Should not raise


class TestMassiveDataSourceAddRemoveTicker:
    """add_ticker() and remove_ticker() behavior."""

    async def test_add_ticker_normalizes_uppercase(self, source: MassiveDataSource):
        source._tickers = ["AAPL"]
        await source.add_ticker("aapl")  # lowercase
        assert source._tickers.count("AAPL") == 1  # No duplicate

    async def test_add_ticker_new(self, source: MassiveDataSource):
        source._tickers = ["AAPL"]
        await source.add_ticker("GOOGL")
        assert "GOOGL" in source._tickers

    async def test_add_ticker_idempotent(self, source: MassiveDataSource):
        source._tickers = ["AAPL"]
        await source.add_ticker("AAPL")
        assert source._tickers.count("AAPL") == 1

    async def test_remove_ticker_normalizes_uppercase(self, source: MassiveDataSource, cache: PriceCache):
        source._tickers = ["AAPL", "GOOGL"]
        cache.update("googl", 175.00)  # cached with wrong case won't matter
        await source.remove_ticker("googl")
        assert "GOOGL" not in source._tickers

    async def test_remove_ticker_clears_cache(self, source: MassiveDataSource, cache: PriceCache):
        cache.update("GOOGL", 175.00)
        source._tickers = ["AAPL", "GOOGL"]
        await source.remove_ticker("GOOGL")
        assert cache.get("GOOGL") is None

    async def test_remove_ticker_not_present_noop(self, source: MassiveDataSource):
        source._tickers = ["AAPL"]
        await source.remove_ticker("GOOGL")  # Should not raise
        assert source._tickers == ["AAPL"]


class TestMassiveDataSourceStop:
    """stop() behavior."""

    async def test_stop_cancels_task(self, source: MassiveDataSource, cache: PriceCache):
        """stop() cancels the background polling task."""
        source._client = MagicMock()
        source._tickers = []  # No tickers to avoid actual poll

        # Manually create a dummy task to simulate running state
        async def dummy_loop():
            try:
                await asyncio.sleep(1000)
            except Exception:
                pass

        source._task = asyncio.create_task(dummy_loop())
        await source.stop()
        assert source._task is None

    async def test_stop_clears_client(self, source: MassiveDataSource):
        source._client = MagicMock()
        source._tickers = []

        async def dummy_loop():
            try:
                await asyncio.sleep(1000)
            except Exception:
                pass

        source._task = asyncio.create_task(dummy_loop())
        await source.stop()
        assert source._client is None

    async def test_stop_idempotent(self, source: MassiveDataSource):
        """Calling stop() twice should not raise."""
        await source.stop()  # Nothing to cancel
        await source.stop()  # Should still not raise


class TestMassiveDataSourceGetTickers:
    """get_tickers() returns a copy."""

    def test_get_tickers_returns_copy(self, source: MassiveDataSource):
        source._tickers = ["AAPL", "GOOGL"]
        result = source.get_tickers()
        result.append("EXTRA")
        assert "EXTRA" not in source._tickers

    def test_get_tickers_empty(self, source: MassiveDataSource):
        source._tickers = []
        assert source.get_tickers() == []
