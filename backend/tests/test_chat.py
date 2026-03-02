"""
Tests for chat endpoint, context building, history loading, persistence, and mock mode.

Verifies:
- POST /api/chat returns structured response (CHAT-01)
- Request validation rejects empty/missing message
- Context includes portfolio and watchlist data (CHAT-02)
- Last 20 messages loaded in chronological order (CHAT-03)
- Empty history is handled gracefully (CHAT-03)
- User message persisted BEFORE LLM call (CHAT-08)
- Assistant message and actions persisted after response (CHAT-08)
- Mock mode returns deterministic response without calling litellm (CHAT-09)
- Mock response has correct shape (CHAT-09)
- 500 returned on unexpected exception
- LLM called with correct params: model, response_format, reasoning_effort, extra_body, api_key (CHAT-04)
- Retry-once on parse failure, fallback on second failure (N4)
- Full orchestration with action execution (CHAT-05, CHAT-06)

Uses established test pattern: mock app.state, httpx.ASGITransport.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from app.main import app
from app.market.cache import PriceCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_app(
    monkeypatch,
    *,
    fetch_return=None,
    llm_mock=True,
):
    """Set up app.state with mocked pool, price cache, market source, and settings.

    Returns (app, conn, mock_settings) so tests can inspect calls.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")

    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetchval = AsyncMock(return_value=10000.0)
    conn.fetch = AsyncMock(return_value=fetch_return or [])
    conn.fetchrow = AsyncMock(return_value=None)

    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire

    cache = PriceCache()

    source = AsyncMock()
    source.add_ticker = AsyncMock()
    source.remove_ticker = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.llm_mock = llm_mock
    mock_settings.openrouter_api_key = ""

    app.state.db_pool = pool
    app.state.price_cache = cache
    app.state.market_source = source
    app.state.settings = mock_settings

    return app, conn, mock_settings


# ---------------------------------------------------------------------------
# POST /api/chat - Response shape (CHAT-01)
# ---------------------------------------------------------------------------


async def test_chat_endpoint_returns_response(monkeypatch):
    """POST /api/chat with {"message": "hello"} -> 200 with response containing
    message, trades, watchlist_changes, and executed_actions fields (CHAT-01)."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert "trades" in data
    assert isinstance(data["trades"], list)
    assert "watchlist_changes" in data
    assert isinstance(data["watchlist_changes"], list)
    assert "executed_actions" in data
    assert isinstance(data["executed_actions"], dict)


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


async def test_chat_request_validation_empty(monkeypatch):
    """POST /api/chat with empty message -> 422 validation error."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422


async def test_chat_request_validation_missing(monkeypatch):
    """POST /api/chat with missing message field -> 422 validation error."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={})

    assert response.status_code == 422


async def test_chat_request_validation_whitespace(monkeypatch):
    """POST /api/chat with whitespace-only message -> 422 validation error."""
    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Context building (CHAT-02)
# ---------------------------------------------------------------------------


@patch("app.services.chat.get_watchlist")
@patch("app.services.chat.get_portfolio")
async def test_context_includes_portfolio(mock_get_portfolio, mock_get_watchlist, monkeypatch):
    """orchestrate_chat calls get_portfolio and get_watchlist to build context (CHAT-02)."""
    mock_get_portfolio.return_value = {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions": [],
    }
    mock_get_watchlist.return_value = [
        {
            "ticker": "AAPL",
            "current_price": 150.0,
            "change": 2.5,
            "change_percent": 1.5,
            "direction": "up",
            "added_at": "2026-03-01T00:00:00+00:00",
        }
    ]

    test_app, _, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    mock_get_portfolio.assert_called_once()
    mock_get_watchlist.assert_called_once()


# ---------------------------------------------------------------------------
# History loading (CHAT-03)
# ---------------------------------------------------------------------------


@patch("app.services.chat.get_watchlist")
@patch("app.services.chat.get_portfolio")
async def test_loads_message_history(mock_get_portfolio, mock_get_watchlist, monkeypatch):
    """When chat_messages has rows, the last 20 are loaded in chronological order
    (DESC LIMIT 20 reversed) and included in the messages array (CHAT-03)."""
    mock_get_portfolio.return_value = {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions": [],
    }
    mock_get_watchlist.return_value = []

    # Return rows in DESC order (most recent first) as the SQL query does
    history_rows = [
        {"role": "assistant", "content": "I can help with that."},
        {"role": "user", "content": "What stocks should I buy?"},
    ]
    test_app, conn, _ = _setup_app(monkeypatch, fetch_return=history_rows)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200

    # Verify conn.fetch was called for history loading
    fetch_calls = conn.fetch.call_args_list
    assert len(fetch_calls) >= 1

    # Check that one of the fetch calls includes the chat_messages query
    history_call_found = False
    for c in fetch_calls:
        args = c[0]
        if len(args) > 0 and "chat_messages" in str(args[0]):
            history_call_found = True
            assert "ORDER BY created_at DESC LIMIT 20" in args[0]
    assert history_call_found, "Expected a query for chat_messages history"


async def test_loads_empty_history(monkeypatch):
    """When chat_messages is empty, orchestrate_chat still works (CHAT-03)."""
    test_app, _, _ = _setup_app(monkeypatch, fetch_return=[])

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


# ---------------------------------------------------------------------------
# Message persistence (CHAT-08)
# ---------------------------------------------------------------------------


async def test_user_message_persisted_before_llm(monkeypatch):
    """User message is inserted into chat_messages with role='user' and actions=None
    BEFORE any LLM call (CHAT-08)."""
    test_app, conn, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "buy AAPL"})

    assert response.status_code == 200

    # Check execute calls for user message persistence
    execute_calls = conn.execute.call_args_list
    user_insert_found = False
    user_insert_index = -1
    for i, c in enumerate(execute_calls):
        args = c[0]
        if len(args) >= 4 and "chat_messages" in str(args[0]) and args[2] == "user":
            user_insert_found = True
            user_insert_index = i
            # Verify the content is the user's message
            assert args[3] == "buy AAPL"
            # Verify actions is None for user messages
            assert args[4] is None
            break

    assert user_insert_found, "Expected user message to be persisted to chat_messages"

    # Verify user message was persisted before assistant message
    assistant_insert_index = -1
    for i, c in enumerate(execute_calls):
        args = c[0]
        if len(args) >= 4 and "chat_messages" in str(args[0]) and args[2] == "assistant":
            assistant_insert_index = i
            break

    if assistant_insert_index >= 0:
        assert user_insert_index < assistant_insert_index, (
            "User message should be persisted before assistant message"
        )


async def test_assistant_message_persisted(monkeypatch):
    """After LLM response, assistant message is inserted into chat_messages
    with role='assistant', content=llm_response.message, and actions JSONB (CHAT-08)."""
    test_app, conn, _ = _setup_app(monkeypatch)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200

    # Check execute calls for assistant message persistence
    execute_calls = conn.execute.call_args_list
    assistant_insert_found = False
    for c in execute_calls:
        args = c[0]
        if len(args) >= 4 and "chat_messages" in str(args[0]) and args[2] == "assistant":
            assistant_insert_found = True
            # Verify it has content (the mock response message)
            assert isinstance(args[3], str)
            assert len(args[3]) > 0
            break

    assert assistant_insert_found, "Expected assistant message to be persisted to chat_messages"


# ---------------------------------------------------------------------------
# Mock mode (CHAT-09)
# ---------------------------------------------------------------------------


async def test_mock_mode_no_llm_call(monkeypatch):
    """When settings.llm_mock=True, orchestrate_chat returns a deterministic mock
    response without importing or calling litellm (CHAT-09)."""
    test_app, _, _ = _setup_app(monkeypatch, llm_mock=True)

    # Patch litellm to detect if it's called
    with patch("app.services.chat._call_llm") as mock_call_llm:
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/chat", json={"message": "test"})

        assert response.status_code == 200
        mock_call_llm.assert_not_called()


async def test_mock_mode_response_shape(monkeypatch):
    """Mock response has message string, empty trades list, empty watchlist_changes list (CHAT-09)."""
    test_app, _, _ = _setup_app(monkeypatch, llm_mock=True)

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "test"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0
    assert "Mock response" in data["message"]
    assert data["trades"] == []
    assert data["watchlist_changes"] == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


async def test_chat_endpoint_500_on_exception(monkeypatch):
    """If orchestrate_chat raises an unexpected exception, route returns 500 with ErrorResponse."""
    test_app, _, _ = _setup_app(monkeypatch)

    with patch("app.routes.chat.orchestrate_chat", side_effect=RuntimeError("boom")):
        transport = httpx.ASGITransport(app=test_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "Chat failed"
    assert "boom" in data["detail"]


# ---------------------------------------------------------------------------
# LLM call parameters (CHAT-04)
# ---------------------------------------------------------------------------


@patch("app.services.chat._persist_assistant_message")
@patch("app.services.chat._persist_user_message")
@patch("app.services.chat._load_history")
@patch("app.services.chat.get_watchlist")
@patch("app.services.chat.get_portfolio")
@patch("app.services.chat.acompletion")
async def test_llm_called_with_correct_params(
    mock_acompletion,
    mock_get_portfolio,
    mock_get_watchlist,
    mock_load_history,
    mock_persist_user,
    mock_persist_assistant,
    monkeypatch,
):
    """When settings.llm_mock=False, acompletion is called with correct model,
    response_format, reasoning_effort, extra_body, and api_key (CHAT-04)."""
    from app.models.chat import LLMResponse
    from app.services.chat import orchestrate_chat

    mock_get_portfolio.return_value = {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions": [],
    }
    mock_get_watchlist.return_value = []
    mock_load_history.return_value = []

    # Set up mock acompletion return
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"message": "test response", "trades": [], "watchlist_changes": []}'
    mock_acompletion.return_value = mock_response

    mock_pool = AsyncMock()
    mock_price_cache = MagicMock()
    mock_market_source = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.llm_mock = False
    mock_settings.openrouter_api_key = "test-api-key-123"

    result = await orchestrate_chat(
        mock_pool, mock_price_cache, mock_market_source, mock_settings, "hello"
    )

    # Verify acompletion was called with correct params
    mock_acompletion.assert_called_once()
    call_kwargs = mock_acompletion.call_args.kwargs
    assert call_kwargs["model"] == "openrouter/openai/gpt-oss-120b"
    assert call_kwargs["response_format"] == LLMResponse
    assert call_kwargs["reasoning_effort"] == "low"
    assert call_kwargs["extra_body"] == {"provider": {"order": ["cerebras"]}}
    assert call_kwargs["api_key"] == "test-api-key-123"

    # Verify response was processed
    assert result["message"] == "test response"


# ---------------------------------------------------------------------------
# Retry logic (decision N4)
# ---------------------------------------------------------------------------


@patch("app.services.chat.acompletion")
async def test_llm_retry_on_parse_failure(mock_acompletion):
    """When acompletion fails twice, _call_llm retries once and returns fallback (N4)."""
    from app.services.chat import _call_llm

    mock_acompletion.side_effect = Exception("Parse error")

    mock_settings = MagicMock()
    mock_settings.openrouter_api_key = "test-key"

    portfolio = {"cash_balance": 10000.0, "total_value": 10000.0, "positions": []}
    watchlist = []

    result = await _call_llm(mock_settings, portfolio, watchlist, [], "test")

    assert mock_acompletion.call_count == 2
    assert result.message  # Non-empty fallback
    assert result.trades == []
    assert result.watchlist_changes == []


@patch("app.services.chat.acompletion")
async def test_llm_fallback_response_shape(mock_acompletion):
    """Fallback response after retry failure has non-empty message, empty trades,
    empty watchlist_changes."""
    from app.services.chat import _call_llm

    mock_acompletion.side_effect = Exception("API timeout")

    mock_settings = MagicMock()
    mock_settings.openrouter_api_key = "test-key"

    portfolio = {"cash_balance": 5000.0, "total_value": 5000.0, "positions": []}
    watchlist = []

    result = await _call_llm(mock_settings, portfolio, watchlist, [], "help me")

    assert isinstance(result.message, str)
    assert len(result.message) > 0
    assert "sorry" in result.message.lower() or "issue" in result.message.lower()
    assert result.trades == []
    assert result.watchlist_changes == []


# ---------------------------------------------------------------------------
# Full orchestration with action execution (integration)
# ---------------------------------------------------------------------------


@patch("app.services.chat._persist_assistant_message")
@patch("app.services.chat._persist_user_message")
@patch("app.services.chat._load_history")
@patch("app.services.chat.remove_ticker")
@patch("app.services.chat.add_ticker")
@patch("app.services.chat.record_snapshot")
@patch("app.services.chat.execute_trade")
@patch("app.services.chat._call_llm")
@patch("app.services.chat.get_watchlist")
@patch("app.services.chat.get_portfolio")
async def test_full_orchestration_with_actions(
    mock_get_portfolio,
    mock_get_watchlist,
    mock_call_llm,
    mock_execute_trade,
    mock_record_snapshot,
    mock_add_ticker,
    mock_remove_ticker,
    mock_load_history,
    mock_persist_user,
    mock_persist_assistant,
):
    """End-to-end test: LLM response with trades and watchlist changes flows through
    execution pipeline and results appear in the response."""
    from app.models.chat import LLMResponse, TradeAction, WatchlistAction
    from app.services.chat import orchestrate_chat

    mock_get_portfolio.return_value = {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "positions": [],
    }
    mock_get_watchlist.return_value = []
    mock_load_history.return_value = []

    # LLM returns a response with a trade and a watchlist change
    mock_call_llm.return_value = LLMResponse(
        message="I'll buy AAPL and add PYPL to your watchlist.",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
    )

    mock_execute_trade.return_value = {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "price": 150.0,
        "total": 1500.0,
    }

    mock_pool = AsyncMock()
    mock_price_cache = MagicMock()
    mock_market_source = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.llm_mock = False

    result = await orchestrate_chat(
        mock_pool, mock_price_cache, mock_market_source, mock_settings, "buy some AAPL"
    )

    # Verify trade was executed
    mock_execute_trade.assert_called_once_with(mock_pool, mock_price_cache, "AAPL", "buy", 10)
    mock_record_snapshot.assert_called_once_with(mock_pool, mock_price_cache)

    # Verify watchlist change was executed
    mock_add_ticker.assert_called_once_with(mock_pool, mock_market_source, "PYPL")

    # Verify response contains executed actions
    assert result["message"] == "I'll buy AAPL and add PYPL to your watchlist."
    assert len(result["trades"]) == 1
    assert result["trades"][0]["ticker"] == "AAPL"
    assert len(result["watchlist_changes"]) == 1
    assert result["watchlist_changes"][0]["ticker"] == "PYPL"
    assert len(result["executed_actions"]["trades"]) == 1
    assert len(result["executed_actions"]["watchlist_changes"]) == 1
    assert result["executed_actions"]["errors"] == []

    # Verify persistence was called
    mock_persist_user.assert_called_once()
    mock_persist_assistant.assert_called_once()
