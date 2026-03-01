"""
Tests for app.market.cache — PriceCache.

13 tests covering:
- First update: previous_price == price, direction is "flat"
- Subsequent updates: correct direction and change computation
- get(), get_all(), get_price(), remove()
- Version counter increments on each update
- __len__ and __contains__
- Thread safety (concurrent access does not corrupt state)
"""

import threading

from app.market.cache import PriceCache


class TestPriceCacheFirstUpdate:
    """First update for a ticker bootstraps with direction='flat'."""

    def test_first_update_previous_price_equals_price(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.previous_price == 190.00
        assert update.price == 190.00

    def test_first_update_direction_flat(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.direction == "flat"

    def test_first_update_change_zero(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.00)
        assert update.change == 0.0


class TestPriceCacheSubsequentUpdates:
    """Subsequent updates compute direction and change correctly."""

    def test_price_up(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 191.00)
        assert update.direction == "up"
        assert update.previous_price == 190.00
        assert update.price == 191.00

    def test_price_down(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 189.00)
        assert update.direction == "down"
        assert update.previous_price == 190.00

    def test_price_unchanged(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 190.00)
        assert update.direction == "flat"

    def test_price_rounds_to_two_decimals(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.123456)
        assert update.price == 190.12


class TestPriceCacheLookup:
    """Tests for get(), get_all(), get_price(), and remove()."""

    def test_get_returns_latest_update(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("AAPL", 191.00)
        result = cache.get("AAPL")
        assert result is not None
        assert result.price == 191.00

    def test_get_unknown_ticker_returns_none(self):
        cache = PriceCache()
        assert cache.get("UNKNOWN") is None

    def test_get_all_returns_all_tickers(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        all_prices = cache.get_all()
        assert "AAPL" in all_prices
        assert "GOOGL" in all_prices
        assert len(all_prices) == 2

    def test_get_all_returns_copy(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        snapshot = cache.get_all()
        snapshot["FAKE"] = None  # type: ignore[assignment]
        assert "FAKE" not in cache.get_all()

    def test_get_price_returns_float(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert cache.get_price("AAPL") == 190.00

    def test_get_price_unknown_returns_none(self):
        cache = PriceCache()
        assert cache.get_price("UNKNOWN") is None

    def test_remove_ticker(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None

    def test_remove_unknown_ticker_noop(self):
        cache = PriceCache()
        cache.remove("UNKNOWN")  # Should not raise


class TestPriceCacheVersion:
    """Version counter increments on each update."""

    def test_initial_version_zero(self):
        cache = PriceCache()
        assert cache.version == 0

    def test_version_increments_on_update(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert cache.version == 1
        cache.update("AAPL", 191.00)
        assert cache.version == 2

    def test_version_increments_per_ticker(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        assert cache.version == 2


class TestPriceCacheContainerProtocol:
    """__len__ and __contains__ work correctly."""

    def test_len_empty(self):
        cache = PriceCache()
        assert len(cache) == 0

    def test_len_with_tickers(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)
        assert len(cache) == 2

    def test_contains_present(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        assert "AAPL" in cache

    def test_contains_absent(self):
        cache = PriceCache()
        assert "AAPL" not in cache


class TestPriceCacheThreadSafety:
    """Concurrent access does not corrupt state."""

    def test_concurrent_updates_do_not_corrupt(self):
        cache = PriceCache()
        errors = []

        def updater(ticker: str, prices: list[float]) -> None:
            try:
                for price in prices:
                    cache.update(ticker, price)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=updater, args=("AAPL", [float(i) for i in range(1, 51)])),
            threading.Thread(target=updater, args=("GOOGL", [float(i) * 2 for i in range(1, 51)])),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # Both tickers should be present
        assert "AAPL" in cache
        assert "GOOGL" in cache
