"""
Tests for action execution in the chat service.

Verifies:
- Trades from LLM response are auto-executed via execute_trade (CHAT-05)
- Portfolio snapshot recorded after each successful trade (PORT-09)
- Watchlist changes from LLM response executed via add_ticker/remove_ticker (CHAT-06)
- Failed actions collected with error details (CHAT-07)
- Partial failures: successes and failures coexist in results
- Empty action lists produce no service calls
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.chat import LLMResponse, TradeAction, WatchlistAction
from app.services.chat import _execute_actions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_pool():
    return AsyncMock()


@pytest.fixture()
def mock_price_cache():
    return MagicMock()


@pytest.fixture()
def mock_market_source():
    return AsyncMock()


# ---------------------------------------------------------------------------
# Trade auto-execution (CHAT-05)
# ---------------------------------------------------------------------------


@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
async def test_trades_auto_executed(
    mock_execute_trade, mock_record_snapshot, mock_pool, mock_price_cache, mock_market_source
):
    """When LLM response has trades, execute_trade is called for each with correct
    ticker/side/quantity and record_snapshot is called after each successful trade (CHAT-05)."""
    mock_execute_trade.return_value = {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "price": 150.0,
        "total": 1500.0,
    }
    llm_response = LLMResponse(
        message="Buying AAPL",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    mock_execute_trade.assert_called_once_with(mock_pool, mock_price_cache, "AAPL", "buy", 10)
    mock_record_snapshot.assert_called_once_with(mock_pool, mock_price_cache)
    assert len(results["trades"]) == 1


@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
async def test_trade_result_included(
    mock_execute_trade, mock_record_snapshot, mock_pool, mock_price_cache, mock_market_source
):
    """Successful trade results are included in executed_actions['trades']."""
    trade_result = {
        "ticker": "GOOGL",
        "side": "sell",
        "quantity": 5,
        "price": 175.0,
        "total": 875.0,
    }
    mock_execute_trade.return_value = trade_result
    llm_response = LLMResponse(
        message="Selling GOOGL",
        trades=[TradeAction(ticker="GOOGL", side="sell", quantity=5)],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    assert results["trades"] == [trade_result]


@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
async def test_trade_failure_collected(
    mock_execute_trade, mock_record_snapshot, mock_pool, mock_price_cache, mock_market_source
):
    """When execute_trade raises ValueError, error is collected with type='trade',
    detail, ticker, side, and quantity (CHAT-07)."""
    mock_execute_trade.side_effect = ValueError("Insufficient cash: need $5000.00, have $100.00")
    llm_response = LLMResponse(
        message="Buying AAPL",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=100)],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    assert len(results["errors"]) == 1
    error = results["errors"][0]
    assert error["type"] == "trade"
    assert "Insufficient cash" in error["detail"]
    assert error["ticker"] == "AAPL"
    assert error["side"] == "buy"
    assert error["quantity"] == 100


@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
async def test_trade_failure_no_snapshot(
    mock_execute_trade, mock_record_snapshot, mock_pool, mock_price_cache, mock_market_source
):
    """When execute_trade raises ValueError, record_snapshot is NOT called for that trade."""
    mock_execute_trade.side_effect = ValueError("Insufficient shares")
    llm_response = LLMResponse(
        message="Selling TSLA",
        trades=[TradeAction(ticker="TSLA", side="sell", quantity=50)],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    mock_record_snapshot.assert_not_called()
    assert len(results["errors"]) == 1


# ---------------------------------------------------------------------------
# Watchlist auto-execution (CHAT-06)
# ---------------------------------------------------------------------------


@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
async def test_watchlist_add_executed(
    mock_add_ticker, mock_remove_ticker, mock_pool, mock_price_cache, mock_market_source
):
    """When LLM response has watchlist_changes with action='add', add_ticker is called (CHAT-06)."""
    llm_response = LLMResponse(
        message="Adding PYPL to watchlist",
        watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    mock_add_ticker.assert_called_once_with(mock_pool, mock_market_source, "PYPL")
    mock_remove_ticker.assert_not_called()


@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
async def test_watchlist_remove_executed(
    mock_add_ticker, mock_remove_ticker, mock_pool, mock_price_cache, mock_market_source
):
    """When LLM response has watchlist_changes with action='remove', remove_ticker is called (CHAT-06)."""
    llm_response = LLMResponse(
        message="Removing META from watchlist",
        watchlist_changes=[WatchlistAction(ticker="META", action="remove")],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    mock_remove_ticker.assert_called_once_with(mock_pool, mock_market_source, "META")
    mock_add_ticker.assert_not_called()


@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
async def test_watchlist_change_result_included(
    mock_add_ticker, mock_remove_ticker, mock_pool, mock_price_cache, mock_market_source
):
    """Successful watchlist changes are included in executed_actions['watchlist_changes']."""
    llm_response = LLMResponse(
        message="Adding PYPL",
        watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    assert len(results["watchlist_changes"]) == 1
    assert results["watchlist_changes"][0] == {"ticker": "PYPL", "action": "add"}


@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
async def test_watchlist_failure_collected(
    mock_add_ticker, mock_remove_ticker, mock_pool, mock_price_cache, mock_market_source
):
    """When add_ticker/remove_ticker raises ValueError, error is collected with type='watchlist' (CHAT-07)."""
    mock_add_ticker.side_effect = ValueError("AAPL already in watchlist")
    llm_response = LLMResponse(
        message="Adding AAPL",
        watchlist_changes=[WatchlistAction(ticker="AAPL", action="add")],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    assert len(results["errors"]) == 1
    error = results["errors"][0]
    assert error["type"] == "watchlist"
    assert "already in watchlist" in error["detail"]
    assert error["ticker"] == "AAPL"
    assert error["action"] == "add"


# ---------------------------------------------------------------------------
# Mixed / edge cases
# ---------------------------------------------------------------------------


@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
async def test_multiple_actions_partial_failure(
    mock_execute_trade,
    mock_record_snapshot,
    mock_add_ticker,
    mock_remove_ticker,
    mock_pool,
    mock_price_cache,
    mock_market_source,
):
    """When some actions succeed and some fail, both are correctly tracked."""
    # First trade succeeds, second fails
    mock_execute_trade.side_effect = [
        {"ticker": "AAPL", "side": "buy", "quantity": 5, "price": 150.0, "total": 750.0},
        ValueError("Insufficient cash"),
    ]
    # First watchlist change succeeds, second fails
    mock_add_ticker.return_value = None
    mock_remove_ticker.side_effect = ValueError("TSLA not in watchlist")

    llm_response = LLMResponse(
        message="Multiple actions",
        trades=[
            TradeAction(ticker="AAPL", side="buy", quantity=5),
            TradeAction(ticker="NVDA", side="buy", quantity=100),
        ],
        watchlist_changes=[
            WatchlistAction(ticker="PYPL", action="add"),
            WatchlistAction(ticker="TSLA", action="remove"),
        ],
    )

    results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

    # One trade success, one trade failure
    assert len(results["trades"]) == 1
    assert results["trades"][0]["ticker"] == "AAPL"

    # One watchlist success, one watchlist failure
    assert len(results["watchlist_changes"]) == 1
    assert results["watchlist_changes"][0]["ticker"] == "PYPL"

    # Two errors total
    assert len(results["errors"]) == 2
    error_types = {e["type"] for e in results["errors"]}
    assert error_types == {"trade", "watchlist"}


async def test_empty_actions_noop(mock_pool, mock_price_cache, mock_market_source):
    """When LLM response has empty trades and watchlist_changes, no services are called."""
    llm_response = LLMResponse(
        message="Just chatting, no actions needed.",
        trades=[],
        watchlist_changes=[],
    )

    with patch("app.services.chat.execute_trade") as mock_trade, \
         patch("app.services.chat.record_snapshot") as mock_snapshot, \
         patch("app.services.chat.add_ticker") as mock_add, \
         patch("app.services.chat.remove_ticker") as mock_remove:

        results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

        mock_trade.assert_not_called()
        mock_snapshot.assert_not_called()
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    assert results == {"trades": [], "watchlist_changes": [], "errors": []}
