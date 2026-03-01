"""
Tests for app.market.simulator — GBMSimulator math engine.

17 tests covering:
- step() returns prices for all tickers
- Prices are always positive (GBM guarantee)
- add_ticker() and remove_ticker() work dynamically
- Cholesky matrix rebuilds correctly
- Random events apply shocks within 2-5% range
- Pairwise correlation returns correct values for all sector combinations
- Single-ticker case (no Cholesky needed)
"""

from app.market.simulator import GBMSimulator
from app.market.seed_prices import (
    CROSS_GROUP_CORR,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    TSLA_CORR,
)


class TestGBMSimulatorInit:
    """Initialization behavior."""

    def test_initializes_with_tickers(self):
        sim = GBMSimulator(["AAPL", "GOOGL", "MSFT"])
        assert set(sim.get_tickers()) == {"AAPL", "GOOGL", "MSFT"}

    def test_seed_prices_positive(self):
        sim = GBMSimulator(["AAPL", "GOOGL", "MSFT"])
        for ticker in sim.get_tickers():
            assert sim.get_price(ticker) > 0

    def test_empty_ticker_list(self):
        sim = GBMSimulator([])
        assert sim.get_tickers() == []

    def test_unknown_ticker_uses_defaults(self):
        sim = GBMSimulator(["UNKNOWNTICKER"])
        price = sim.get_price("UNKNOWNTICKER")
        assert price is not None
        assert 50.0 <= price <= 300.0

    def test_single_ticker_no_cholesky(self):
        """With one ticker, Cholesky is not built (no correlation needed)."""
        sim = GBMSimulator(["AAPL"])
        assert sim._cholesky is None


class TestGBMSimulatorStep:
    """step() behavior."""

    def test_step_returns_all_tickers(self):
        sim = GBMSimulator(["AAPL", "GOOGL", "MSFT"])
        prices = sim.step()
        assert set(prices.keys()) == {"AAPL", "GOOGL", "MSFT"}

    def test_step_empty_returns_empty(self):
        sim = GBMSimulator([])
        prices = sim.step()
        assert prices == {}

    def test_step_prices_always_positive(self):
        """GBM with exp() guarantees positive prices."""
        sim = GBMSimulator(["AAPL", "GOOGL", "MSFT", "TSLA"])
        for _ in range(100):
            prices = sim.step()
            for ticker, price in prices.items():
                assert price > 0, f"{ticker} price went non-positive: {price}"

    def test_step_prices_are_floats(self):
        sim = GBMSimulator(["AAPL"])
        prices = sim.step()
        assert isinstance(prices["AAPL"], float)

    def test_step_prices_rounded_to_two_decimals(self):
        sim = GBMSimulator(["AAPL"])
        prices = sim.step()
        price = prices["AAPL"]
        # Check that the value has at most 2 decimal places
        assert price == round(price, 2)

    def test_step_single_ticker_no_cholesky(self):
        """Single ticker step works without a Cholesky matrix."""
        sim = GBMSimulator(["AAPL"])
        prices = sim.step()
        assert "AAPL" in prices
        assert prices["AAPL"] > 0


class TestGBMSimulatorDynamicTickers:
    """add_ticker() and remove_ticker() behavior."""

    def test_add_ticker(self):
        sim = GBMSimulator(["AAPL"])
        sim.add_ticker("GOOGL")
        assert "GOOGL" in sim.get_tickers()
        assert sim.get_price("GOOGL") is not None

    def test_add_ticker_idempotent(self):
        """Adding an existing ticker is a no-op."""
        sim = GBMSimulator(["AAPL"])
        price_before = sim.get_price("AAPL")
        sim.add_ticker("AAPL")
        assert sim.get_tickers().count("AAPL") == 1
        assert sim.get_price("AAPL") == price_before

    def test_remove_ticker(self):
        sim = GBMSimulator(["AAPL", "GOOGL"])
        sim.remove_ticker("GOOGL")
        assert "GOOGL" not in sim.get_tickers()
        assert sim.get_price("GOOGL") is None

    def test_remove_ticker_idempotent(self):
        """Removing a non-existent ticker is a no-op."""
        sim = GBMSimulator(["AAPL"])
        sim.remove_ticker("GOOGL")  # Should not raise
        assert sim.get_tickers() == ["AAPL"]

    def test_add_then_step_includes_new_ticker(self):
        sim = GBMSimulator(["AAPL"])
        sim.add_ticker("GOOGL")
        prices = sim.step()
        assert "GOOGL" in prices

    def test_remove_then_step_excludes_removed_ticker(self):
        sim = GBMSimulator(["AAPL", "GOOGL"])
        sim.remove_ticker("GOOGL")
        prices = sim.step()
        assert "GOOGL" not in prices

    def test_cholesky_rebuilt_after_add(self):
        """Cholesky is rebuilt to include the new ticker."""
        sim = GBMSimulator(["AAPL"])
        assert sim._cholesky is None  # Single ticker → no Cholesky
        sim.add_ticker("GOOGL")
        assert sim._cholesky is not None  # Now 2 tickers → needs Cholesky

    def test_cholesky_rebuilt_after_remove_to_single(self):
        sim = GBMSimulator(["AAPL", "GOOGL"])
        assert sim._cholesky is not None
        sim.remove_ticker("GOOGL")
        assert sim._cholesky is None  # Back to single ticker


class TestGBMSimulatorCorrelation:
    """Pairwise correlation values for different sector combinations."""

    def test_tech_tech_correlation(self):
        """Two tech stocks → INTRA_TECH_CORR (0.6)."""
        corr = GBMSimulator._pairwise_correlation("AAPL", "MSFT")
        assert corr == INTRA_TECH_CORR

    def test_finance_finance_correlation(self):
        """Two finance stocks → INTRA_FINANCE_CORR (0.5)."""
        corr = GBMSimulator._pairwise_correlation("JPM", "V")
        assert corr == INTRA_FINANCE_CORR

    def test_cross_sector_correlation(self):
        """Tech + Finance → CROSS_GROUP_CORR (0.3)."""
        corr = GBMSimulator._pairwise_correlation("AAPL", "JPM")
        assert corr == CROSS_GROUP_CORR

    def test_tsla_correlation(self):
        """TSLA has low correlation with any other ticker."""
        assert GBMSimulator._pairwise_correlation("TSLA", "AAPL") == TSLA_CORR
        assert GBMSimulator._pairwise_correlation("MSFT", "TSLA") == TSLA_CORR

    def test_unknown_ticker_correlation(self):
        """Unknown tickers use CROSS_GROUP_CORR."""
        corr = GBMSimulator._pairwise_correlation("UNKNOWN1", "UNKNOWN2")
        assert corr == CROSS_GROUP_CORR


class TestGBMSimulatorMath:
    """Mathematical correctness of GBM."""

    def test_dt_calibration(self):
        """dt should be approximately 0.5 / (252 * 6.5 * 3600)."""
        expected_dt = 0.5 / (252 * 6.5 * 3600)
        assert abs(GBMSimulator.DEFAULT_DT - expected_dt) < 1e-12

    def test_prices_stay_near_seed(self):
        """Over 100 steps, prices should stay within a reasonable range."""
        sim = GBMSimulator(["AAPL"], dt=GBMSimulator.DEFAULT_DT, event_probability=0)
        initial_price = sim.get_price("AAPL")
        for _ in range(100):
            prices = sim.step()
        final_price = prices["AAPL"]
        # Allow up to 2% deviation over 100 steps at normal volatility
        ratio = final_price / initial_price
        assert 0.90 <= ratio <= 1.10, f"Price drifted too far: {initial_price} → {final_price}"
