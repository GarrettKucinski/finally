"""
Tests for app.market.models — PriceUpdate dataclass.

11 tests covering:
- Computed properties: change, change_percent, direction
- Edge cases: zero previous price, equal prices (flat), negative change
- to_dict() serialization
- Frozen immutability
"""

from dataclasses import FrozenInstanceError

from app.market.models import PriceUpdate


class TestPriceUpdateProperties:
    """Tests for computed properties."""

    def test_direction_up(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
        assert update.direction == "up"

    def test_direction_down(self):
        update = PriceUpdate(ticker="AAPL", price=189.00, previous_price=190.00)
        assert update.direction == "down"

    def test_direction_flat(self):
        update = PriceUpdate(ticker="AAPL", price=190.00, previous_price=190.00)
        assert update.direction == "flat"

    def test_change_positive(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
        assert update.change == 1.5

    def test_change_negative(self):
        update = PriceUpdate(ticker="AAPL", price=188.00, previous_price=190.00)
        assert update.change == -2.0

    def test_change_zero(self):
        update = PriceUpdate(ticker="AAPL", price=190.00, previous_price=190.00)
        assert update.change == 0.0

    def test_change_percent_positive(self):
        update = PriceUpdate(ticker="AAPL", price=191.00, previous_price=190.00)
        # (191 - 190) / 190 * 100 = 0.5263%
        assert abs(update.change_percent - 0.5263) < 0.001

    def test_change_percent_negative(self):
        update = PriceUpdate(ticker="AAPL", price=189.00, previous_price=190.00)
        # (189 - 190) / 190 * 100 = -0.5263%
        assert abs(update.change_percent - (-0.5263)) < 0.001

    def test_change_percent_zero_previous_price(self):
        """Zero previous_price returns 0.0 (no division by zero)."""
        update = PriceUpdate(ticker="AAPL", price=100.00, previous_price=0.0)
        assert update.change_percent == 0.0

    def test_change_percent_flat(self):
        update = PriceUpdate(ticker="AAPL", price=190.00, previous_price=190.00)
        assert update.change_percent == 0.0


class TestPriceUpdateSerialization:
    """Tests for to_dict() serialization."""

    def test_to_dict_keys(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00, timestamp=1709312400.0)
        result = update.to_dict()
        expected_keys = {"ticker", "price", "previous_price", "timestamp", "change", "change_percent", "direction"}
        assert set(result.keys()) == expected_keys

    def test_to_dict_values(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00, timestamp=1709312400.0)
        result = update.to_dict()
        assert result["ticker"] == "AAPL"
        assert result["price"] == 191.50
        assert result["previous_price"] == 190.00
        assert result["timestamp"] == 1709312400.0
        assert result["direction"] == "up"

    def test_to_dict_computed_fields(self):
        update = PriceUpdate(ticker="GOOGL", price=175.00, previous_price=175.00, timestamp=0.0)
        result = update.to_dict()
        assert result["change"] == 0.0
        assert result["change_percent"] == 0.0
        assert result["direction"] == "flat"


class TestPriceUpdateImmutability:
    """Tests for frozen dataclass behavior."""

    def test_frozen_raises_on_assignment(self):
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
        try:
            update.price = 200.0  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except (FrozenInstanceError, AttributeError):
            pass  # Either exception is acceptable

    def test_default_timestamp_is_set(self):
        """PriceUpdate sets timestamp automatically if not provided."""
        update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
        assert isinstance(update.timestamp, float)
        assert update.timestamp > 0
