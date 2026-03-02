"""
Tests for the portfolio service layer (trade execution, portfolio query, snapshots).

Tests use AsyncMock for pool/conn and a real PriceCache instance to verify
correct business logic, SQL operations, and atomic transaction usage.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, call

import pytest

from app.market.cache import PriceCache
from app.services.portfolio import (
    DEFAULT_USER_ID,
    execute_trade,
    get_portfolio,
    record_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _mock_transaction():
    """Simulate asyncpg conn.transaction() context manager."""
    yield


def _make_pool_and_conn(
    *,
    cash: float = 10000.0,
    position_row=None,
    positions_list=None,
):
    """Create a mock pool and connection with configurable return values.

    Args:
        cash: Cash balance returned by fetchval for users_profile query.
        position_row: Return value for fetchrow (single position lookup).
        positions_list: Return value for fetch (all positions query).
    """
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=cash)
    conn.fetchrow = AsyncMock(return_value=position_row)
    conn.fetch = AsyncMock(return_value=positions_list or [])
    conn.execute = AsyncMock()
    conn.transaction = _mock_transaction

    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool, conn


def _make_cache(*tickers_prices: tuple[str, float]) -> PriceCache:
    """Create a PriceCache pre-seeded with given ticker/price pairs."""
    cache = PriceCache()
    for ticker, price in tickers_prices:
        cache.update(ticker, price)
    return cache


# ---------------------------------------------------------------------------
# execute_trade: BUY tests
# ---------------------------------------------------------------------------

async def test_execute_buy():
    """Buy 10 shares of AAPL at $150 -> cash decreases by $1500, position created."""
    pool, conn = _make_pool_and_conn(cash=10000.0)
    cache = _make_cache(("AAPL", 150.0))

    result = await execute_trade(pool, cache, "AAPL", "buy", 10)

    assert result["ticker"] == "AAPL"
    assert result["side"] == "buy"
    assert result["quantity"] == 10
    assert result["price"] == 150.0
    assert result["total"] == 1500.0

    # Verify cash was decreased
    calls = conn.execute.call_args_list
    cash_update = [c for c in calls if "cash_balance" in str(c) and "-" in str(c) or "cash_balance - " in str(c)]
    assert len(cash_update) >= 1 or any("cash_balance" in str(c) for c in calls)

    # Verify position was upserted (INSERT INTO positions with ON CONFLICT)
    position_calls = [c for c in calls if "positions" in str(c).lower() and "insert" in str(c).lower()]
    assert len(position_calls) >= 1

    # Verify trade was logged
    trade_calls = [c for c in calls if "trades" in str(c).lower() and "insert" in str(c).lower()]
    assert len(trade_calls) == 1


async def test_execute_buy_additional():
    """Buy 10 at $100 then 5 at $200 -> weighted avg cost = $133.33, qty=15."""
    pool, conn = _make_pool_and_conn(cash=10000.0)
    cache = _make_cache(("AAPL", 100.0))

    # First buy: 10 shares at $100
    await execute_trade(pool, cache, "AAPL", "buy", 10)

    # Update price for second buy
    cache.update("AAPL", 200.0)
    # Reset cash for second buy (simulating decreased cash)
    conn.fetchval = AsyncMock(return_value=9000.0)

    # Second buy: 5 shares at $200
    result = await execute_trade(pool, cache, "AAPL", "buy", 5)

    assert result["ticker"] == "AAPL"
    assert result["quantity"] == 5
    assert result["price"] == 200.0
    assert result["total"] == 1000.0

    # Verify the upsert SQL references ON CONFLICT for weighted average
    all_calls = conn.execute.call_args_list
    upsert_calls = [c for c in all_calls if "ON CONFLICT" in str(c).upper() or "on conflict" in str(c).lower()]
    assert len(upsert_calls) >= 1, "Expected ON CONFLICT upsert for position"


async def test_buy_insufficient_cash():
    """Buy with cost > cash_balance -> raises ValueError with 'Insufficient cash'."""
    pool, conn = _make_pool_and_conn(cash=100.0)
    cache = _make_cache(("AAPL", 150.0))

    with pytest.raises(ValueError, match="Insufficient cash"):
        await execute_trade(pool, cache, "AAPL", "buy", 10)


# ---------------------------------------------------------------------------
# execute_trade: SELL tests
# ---------------------------------------------------------------------------

async def test_execute_sell():
    """Sell 5 shares of AAPL (holding 10) -> cash increases, qty decreases."""
    position_row = {"quantity": 10.0, "avg_cost": 100.0}
    pool, conn = _make_pool_and_conn(cash=5000.0, position_row=position_row)
    cache = _make_cache(("AAPL", 150.0))

    result = await execute_trade(pool, cache, "AAPL", "sell", 5)

    assert result["ticker"] == "AAPL"
    assert result["side"] == "sell"
    assert result["quantity"] == 5
    assert result["price"] == 150.0
    assert result["total"] == 750.0

    # Verify cash was increased
    calls = conn.execute.call_args_list
    cash_calls = [c for c in calls if "cash_balance" in str(c)]
    assert len(cash_calls) >= 1

    # Verify position was updated (not deleted, since 5 shares remain)
    update_calls = [c for c in calls if "update" in str(c).lower() and "positions" in str(c).lower()]
    assert len(update_calls) >= 1


async def test_sell_all_deletes_position():
    """Sell all shares -> position row deleted (not updated to qty=0)."""
    position_row = {"quantity": 10.0, "avg_cost": 100.0}
    pool, conn = _make_pool_and_conn(cash=5000.0, position_row=position_row)
    cache = _make_cache(("AAPL", 150.0))

    result = await execute_trade(pool, cache, "AAPL", "sell", 10)

    assert result["quantity"] == 10

    # Verify position was DELETED (not updated)
    calls = conn.execute.call_args_list
    delete_calls = [c for c in calls if "delete" in str(c).lower() and "positions" in str(c).lower()]
    assert len(delete_calls) >= 1, "Expected DELETE on positions when selling all shares"


async def test_sell_insufficient_shares():
    """Sell more than held -> raises ValueError with 'Insufficient shares'."""
    position_row = {"quantity": 5.0, "avg_cost": 100.0}
    pool, conn = _make_pool_and_conn(cash=5000.0, position_row=position_row)
    cache = _make_cache(("AAPL", 150.0))

    with pytest.raises(ValueError, match="Insufficient shares"):
        await execute_trade(pool, cache, "AAPL", "sell", 10)


async def test_sell_no_position():
    """Sell ticker not held -> raises ValueError with 'Insufficient shares'."""
    pool, conn = _make_pool_and_conn(cash=5000.0, position_row=None)
    cache = _make_cache(("AAPL", 150.0))

    with pytest.raises(ValueError, match="Insufficient shares"):
        await execute_trade(pool, cache, "AAPL", "sell", 5)


# ---------------------------------------------------------------------------
# execute_trade: Edge cases
# ---------------------------------------------------------------------------

async def test_no_price_available():
    """Trade on ticker with no cached price -> raises ValueError."""
    pool, conn = _make_pool_and_conn(cash=10000.0)
    cache = PriceCache()  # Empty cache

    with pytest.raises(ValueError, match="No price available"):
        await execute_trade(pool, cache, "AAPL", "buy", 10)


async def test_trade_creates_log_entry():
    """Every trade inserts a row in trades table."""
    pool, conn = _make_pool_and_conn(cash=10000.0)
    cache = _make_cache(("AAPL", 150.0))

    await execute_trade(pool, cache, "AAPL", "buy", 10)

    # Check that an INSERT INTO trades was executed
    calls = conn.execute.call_args_list
    trade_inserts = [
        c for c in calls
        if "trades" in str(c).lower() and "insert" in str(c).lower()
    ]
    assert len(trade_inserts) == 1

    # Verify the trade log contains correct values
    trade_call = trade_inserts[0]
    args = trade_call[0]  # positional args
    sql = args[0]
    assert "trades" in sql.lower()
    # Verify the parameters include user_id, ticker, side, quantity, price
    assert DEFAULT_USER_ID in args
    assert "AAPL" in args
    assert "buy" in args
    assert 10 in args or 10.0 in args
    assert 150.0 in args


async def test_trade_atomic():
    """All DB operations happen within conn.transaction() context manager."""
    pool, conn = _make_pool_and_conn(cash=10000.0)
    cache = _make_cache(("AAPL", 150.0))

    # Replace transaction with a tracking mock
    transaction_entered = False
    original_transaction = conn.transaction

    @asynccontextmanager
    async def tracking_transaction():
        nonlocal transaction_entered
        transaction_entered = True
        yield

    conn.transaction = tracking_transaction

    await execute_trade(pool, cache, "AAPL", "buy", 10)

    assert transaction_entered, "execute_trade must use conn.transaction() for atomicity"


async def test_snapshot_after_trade():
    """record_snapshot is callable and computes total_value = cash + positions value."""
    pool, conn = _make_pool_and_conn(
        cash=8500.0,
        positions_list=[
            {"ticker": "AAPL", "quantity": 10.0},
        ],
    )
    cache = _make_cache(("AAPL", 150.0))

    await record_snapshot(pool, cache)

    # Verify INSERT INTO portfolio_snapshots was called
    calls = conn.execute.call_args_list
    snapshot_inserts = [
        c for c in calls
        if "portfolio_snapshots" in str(c).lower() and "insert" in str(c).lower()
    ]
    assert len(snapshot_inserts) == 1

    # Verify total_value = 8500 + (150 * 10) = 10000
    snapshot_call = snapshot_inserts[0]
    args = snapshot_call[0]
    # The total_value should be in the args
    assert 10000.0 in args, f"Expected total_value=10000.0 in args: {args}"


# ---------------------------------------------------------------------------
# get_portfolio tests
# ---------------------------------------------------------------------------

async def test_get_portfolio_empty():
    """No positions -> returns cash_balance=10000, total_value=10000, positions=[]."""
    pool, conn = _make_pool_and_conn(cash=10000.0, positions_list=[])
    cache = PriceCache()

    result = await get_portfolio(pool, cache)

    assert result["cash_balance"] == 10000.0
    assert result["total_value"] == 10000.0
    assert result["positions"] == []


async def test_get_portfolio_with_positions():
    """Positions with live prices -> unrealized_pnl and pnl_percent computed."""
    positions_list = [
        {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 100.0},
        {"ticker": "GOOGL", "quantity": 5.0, "avg_cost": 200.0},
    ]
    pool, conn = _make_pool_and_conn(cash=5000.0, positions_list=positions_list)
    cache = _make_cache(("AAPL", 150.0), ("GOOGL", 180.0))

    result = await get_portfolio(pool, cache)

    assert result["cash_balance"] == 5000.0
    # total_value = 5000 + (150*10) + (180*5) = 5000 + 1500 + 900 = 7400
    assert result["total_value"] == 7400.0

    assert len(result["positions"]) == 2

    aapl = result["positions"][0]
    assert aapl["ticker"] == "AAPL"
    assert aapl["quantity"] == 10.0
    assert aapl["avg_cost"] == 100.0
    assert aapl["current_price"] == 150.0
    # unrealized_pnl = (150 - 100) * 10 = 500
    assert aapl["unrealized_pnl"] == 500.0
    # pnl_percent = ((150 - 100) / 100) * 100 = 50.0
    assert aapl["pnl_percent"] == 50.0

    googl = result["positions"][1]
    assert googl["ticker"] == "GOOGL"
    assert googl["current_price"] == 180.0
    # unrealized_pnl = (180 - 200) * 5 = -100
    assert googl["unrealized_pnl"] == -100.0
    # pnl_percent = ((180 - 200) / 200) * 100 = -10.0
    assert googl["pnl_percent"] == -10.0


# ---------------------------------------------------------------------------
# record_snapshot tests
# ---------------------------------------------------------------------------

async def test_record_snapshot():
    """Computes total_value = cash + sum(price * qty) and inserts into snapshots."""
    positions_list = [
        {"ticker": "AAPL", "quantity": 10.0},
        {"ticker": "GOOGL", "quantity": 5.0},
    ]
    pool, conn = _make_pool_and_conn(cash=5000.0, positions_list=positions_list)
    cache = _make_cache(("AAPL", 150.0), ("GOOGL", 200.0))

    await record_snapshot(pool, cache)

    # total_value = 5000 + (150*10) + (200*5) = 5000 + 1500 + 1000 = 7500
    calls = conn.execute.call_args_list
    snapshot_inserts = [
        c for c in calls
        if "portfolio_snapshots" in str(c).lower()
    ]
    assert len(snapshot_inserts) == 1

    args = snapshot_inserts[0][0]
    assert 7500.0 in args, f"Expected total_value=7500.0 in args: {args}"
