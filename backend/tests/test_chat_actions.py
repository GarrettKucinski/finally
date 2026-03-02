"""
Tests for action execution in the chat service.

Verifies:
- Trades from LLM response are NEVER auto-executed (deterministic guardrail)
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
# Trade guardrail — trades are NEVER executed
# ---------------------------------------------------------------------------


async def test_trades_never_executed(mock_pool, mock_price_cache, mock_market_source):
    """Even when LLM response contains trades, execute_trade is never called.

    This is the core deterministic guardrail: the backend never auto-executes
    trades from LLM responses. Trades are returned as proposals for the
    frontend to render with Confirm/Dismiss buttons.
    """
    llm_response = LLMResponse(
        message="Buying AAPL",
        trades=[
            TradeAction(ticker="AAPL", side="buy", quantity=10),
            TradeAction(ticker="GOOGL", side="sell", quantity=5),
        ],
    )

    with patch("app.services.chat.add_ticker") as mock_add, \
         patch("app.services.chat.remove_ticker") as mock_remove:
        results = await _execute_actions(
            mock_pool, mock_price_cache, mock_market_source, llm_response
        )

        # No trade-related service calls whatsoever
        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    # Results contain no trades key
    assert "trades" not in results
    assert results == {"watchlist_changes": [], "errors": []}


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
async def test_multiple_actions_partial_failure(
    mock_add_ticker,
    mock_remove_ticker,
    mock_pool,
    mock_price_cache,
    mock_market_source,
):
    """When some watchlist actions succeed and some fail, both are correctly tracked.

    Trades in the LLM response are completely ignored by _execute_actions.
    """
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

    # No trades key in results (trades are never executed)
    assert "trades" not in results

    # One watchlist success, one watchlist failure
    assert len(results["watchlist_changes"]) == 1
    assert results["watchlist_changes"][0]["ticker"] == "PYPL"

    # One error (watchlist only)
    assert len(results["errors"]) == 1
    assert results["errors"][0]["type"] == "watchlist"


async def test_empty_actions_noop(mock_pool, mock_price_cache, mock_market_source):
    """When LLM response has empty trades and watchlist_changes, no services are called."""
    llm_response = LLMResponse(
        message="Just chatting, no actions needed.",
        trades=[],
        watchlist_changes=[],
    )

    with patch("app.services.chat.add_ticker") as mock_add, \
         patch("app.services.chat.remove_ticker") as mock_remove:

        results = await _execute_actions(mock_pool, mock_price_cache, mock_market_source, llm_response)

        mock_add.assert_not_called()
        mock_remove.assert_not_called()

    assert results == {"watchlist_changes": [], "errors": []}
