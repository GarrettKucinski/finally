"""Chat service -- orchestrates context building, LLM calls, action execution, and persistence.

This is the central orchestration layer for the AI chat feature.
Routes call orchestrate_chat() which coordinates:
1. Building portfolio context (reusing existing services)
2. Loading conversation history (last 20 messages)
3. Calling the LLM (or returning a mock response)
4. Executing trades and watchlist changes (Plan 03-02)
5. Persisting messages to the database
"""

from __future__ import annotations

import json
import logging

from asyncpg import Pool
from litellm import acompletion

from app.config import Settings
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.models.chat import LLMResponse
from app.services.portfolio import execute_trade, get_portfolio, record_snapshot
from app.services.watchlist import add_ticker, get_watchlist, remove_ticker

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated trading platform.

You help users manage their simulated portfolio by:
- Analyzing portfolio composition, risk concentration, and P&L
- Suggesting trades with clear reasoning
- Executing trades when asked (buy/sell at current market price)
- Managing the watchlist (adding/removing tickers)

Be concise and data-driven. Format numbers with appropriate precision.
When suggesting or executing trades, always reference the current price and portfolio impact.

IMPORTANT: You operate in a simulated environment with virtual money. There is no real financial risk.

Current Portfolio State:
{portfolio_context}

Current Watchlist:
{watchlist_context}"""


async def orchestrate_chat(
    pool: Pool,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    settings: Settings,
    user_message: str,
) -> dict:
    """Full chat flow: context -> persist user msg -> LLM -> execute actions -> persist assistant msg -> respond.

    Returns a dict matching ChatResponse shape.
    """
    # 1. Build portfolio context
    portfolio = await get_portfolio(pool, price_cache)
    watchlist = await get_watchlist(pool, price_cache)

    # 2. Load conversation history (last 20 messages)
    history = await _load_history(pool)

    # 3. Persist user message BEFORE LLM call (Pitfall 6: survives LLM failures)
    await _persist_user_message(pool, user_message)

    # 4. Call LLM (or mock)
    if settings.llm_mock:
        llm_response = _mock_response(user_message)
    else:
        llm_response = await _call_llm(settings, portfolio, watchlist, history, user_message)

    # 5. Execute trades and watchlist changes (stub for Plan 03-02)
    executed_actions = await _execute_actions(pool, price_cache, market_source, llm_response)

    # 6. Persist assistant message
    await _persist_assistant_message(pool, llm_response, executed_actions)

    # 7. Return response
    return {
        "message": llm_response.message,
        "trades": [t.model_dump() for t in llm_response.trades],
        "watchlist_changes": [w.model_dump() for w in llm_response.watchlist_changes],
        "executed_actions": executed_actions,
    }


def _build_context(portfolio: dict, watchlist: list[dict]) -> tuple[str, str]:
    """Format portfolio and watchlist data for the system prompt."""
    # Portfolio context
    lines = []
    lines.append(f"Cash: ${portfolio['cash_balance']:,.2f}")
    lines.append(f"Total Value: ${portfolio['total_value']:,.2f}")
    if portfolio["positions"]:
        lines.append("Positions:")
        for p in portfolio["positions"]:
            price_str = f"${p['current_price']:,.2f}" if p["current_price"] else "N/A"
            lines.append(
                f"  {p['ticker']}: {p['quantity']} shares @ avg ${p['avg_cost']:,.2f}, "
                f"current {price_str}, P&L ${p['unrealized_pnl']:,.2f} ({p['pnl_percent']:+.1f}%)"
            )
    else:
        lines.append("Positions: None")
    portfolio_context = "\n".join(lines)

    # Watchlist context
    wl_lines = []
    for w in watchlist:
        price_str = f"${w['current_price']:,.2f}" if w["current_price"] else "N/A"
        change_str = f"{w['change_percent']:+.2f}%" if w["change_percent"] is not None else "N/A"
        wl_lines.append(f"  {w['ticker']}: {price_str} ({change_str})")
    watchlist_context = "\n".join(wl_lines) if wl_lines else "  Empty"

    return portfolio_context, watchlist_context


def _build_messages(
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """Construct the messages array for the LLM call."""
    portfolio_context, watchlist_context = _build_context(portfolio, watchlist)

    system_msg = SYSTEM_PROMPT.format(
        portfolio_context=portfolio_context,
        watchlist_context=watchlist_context,
    )

    messages = [{"role": "system", "content": system_msg}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


async def _load_history(pool: Pool) -> list[dict]:
    """Load the last 20 chat messages in chronological order."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM chat_messages WHERE user_id = $1 "
            "ORDER BY created_at DESC LIMIT 20",
            DEFAULT_USER_ID,
        )
    # Reverse to chronological order for the LLM
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


async def _call_llm(
    settings: Settings,
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
    user_message: str,
) -> LLMResponse:
    """Call the LLM via LiteLLM -> OpenRouter with Cerebras inference.

    Uses acompletion (async) to avoid blocking the event loop.

    Implements retry-once on parse failure (decision N4).
    """
    MODEL = "openrouter/openai/gpt-oss-120b"
    EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

    messages = _build_messages(portfolio, watchlist, history, user_message)

    for attempt in range(2):  # retry once on parse failure (decision N4)
        try:
            response = await acompletion(
                model=MODEL,
                messages=messages,
                response_format=LLMResponse,
                reasoning_effort="low",
                extra_body=EXTRA_BODY,
                api_key=settings.openrouter_api_key,
            )
            content = response.choices[0].message.content
            return LLMResponse.model_validate_json(content)
        except Exception as e:
            if attempt == 0:
                logger.warning("LLM response parse failed (attempt 1), retrying: %s", e)
                continue
            logger.error("LLM response parse failed after retry: %s", e)
            # Return a fallback error message with no actions (decision N4)
            return LLMResponse(
                message="I'm sorry, I encountered an issue processing your request. Please try again.",
                trades=[],
                watchlist_changes=[],
            )

    # Should never reach here, but satisfy type checker
    return LLMResponse(
        message="I'm sorry, I encountered an issue processing your request. Please try again.",
        trades=[],
        watchlist_changes=[],
    )


def _mock_response(user_message: str) -> LLMResponse:
    """Return a deterministic mock response for testing (CHAT-09)."""
    return LLMResponse(
        message=f"Mock response: I received your message about '{user_message}'. "
        "As a mock AI assistant, I can confirm the chat system is working correctly.",
        trades=[],
        watchlist_changes=[],
    )


async def _execute_actions(
    pool: Pool,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    llm_response: LLMResponse,
) -> dict:
    """Execute trades and watchlist changes from the LLM response.

    Each action is wrapped in try/except. Successes and failures are
    tracked separately so the response includes full execution results.
    A portfolio snapshot is recorded after each successful trade (PORT-09).
    """
    results: dict = {"trades": [], "watchlist_changes": [], "errors": []}

    for trade in llm_response.trades:
        try:
            trade_result = await execute_trade(
                pool, price_cache, trade.ticker, trade.side, trade.quantity
            )
            await record_snapshot(pool, price_cache)
            results["trades"].append(trade_result)
        except ValueError as e:
            results["errors"].append({
                "type": "trade",
                "detail": str(e),
                "ticker": trade.ticker,
                "side": trade.side,
                "quantity": trade.quantity,
            })

    for change in llm_response.watchlist_changes:
        try:
            if change.action == "add":
                await add_ticker(pool, market_source, change.ticker)
            elif change.action == "remove":
                await remove_ticker(pool, market_source, change.ticker)
            results["watchlist_changes"].append(change.model_dump())
        except ValueError as e:
            results["errors"].append({
                "type": "watchlist",
                "detail": str(e),
                "ticker": change.ticker,
                "action": change.action,
            })

    return results


async def _persist_user_message(pool: Pool, user_message: str) -> None:
    """Persist the user's message to chat_messages."""
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, actions) VALUES ($1, $2, $3, $4)",
            DEFAULT_USER_ID,
            "user",
            user_message,
            None,
        )


async def _persist_assistant_message(
    pool: Pool, llm_response: LLMResponse, executed_actions: dict
) -> None:
    """Persist the assistant's message and executed actions to chat_messages."""
    actions_json = json.dumps(executed_actions) if executed_actions else None
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, actions) VALUES ($1, $2, $3, $4::jsonb)",
            DEFAULT_USER_ID,
            "assistant",
            llm_response.message,
            actions_json,
        )
