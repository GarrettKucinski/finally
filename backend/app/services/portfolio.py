"""Portfolio service layer -- trade execution, portfolio query, snapshot recording.

Business logic for the portfolio API endpoints. Routes stay thin; all
validation, DB operations, and calculations live here.

Key design:
- execute_trade: atomic transaction wrapping position upsert + cash update + trade log
- get_portfolio: enriches DB positions with live PriceCache prices for P&L
- record_snapshot: computes total portfolio value and persists to portfolio_snapshots
"""

from __future__ import annotations

from asyncpg import Pool

from app.market.cache import PriceCache

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


async def execute_trade(
    pool: Pool,
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
) -> dict:
    """Execute a trade atomically. Returns trade details or raises ValueError.

    For BUY:
        - Validates sufficient cash
        - Decreases cash balance
        - Upserts position with weighted average cost
        - Logs trade

    For SELL:
        - Validates sufficient shares
        - Increases cash balance
        - Updates or deletes position (delete at zero quantity)
        - Logs trade

    All operations happen within a single DB transaction for atomicity.
    """
    price = price_cache.get_price(ticker)
    if price is None:
        raise ValueError(f"No price available for {ticker}")

    total = round(price * quantity, 2)

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Read current cash balance
            cash = await conn.fetchval(
                "SELECT cash_balance FROM users_profile WHERE user_id = $1",
                DEFAULT_USER_ID,
            )

            if side == "buy":
                if cash < total:
                    raise ValueError(
                        f"Insufficient cash: need ${total:.2f}, have ${cash:.2f}"
                    )

                # Decrease cash
                await conn.execute(
                    "UPDATE users_profile SET cash_balance = cash_balance - $1 WHERE user_id = $2",
                    total,
                    DEFAULT_USER_ID,
                )

                # Upsert position with weighted average cost
                await conn.execute(
                    """
                    INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (user_id, ticker) DO UPDATE SET
                        avg_cost = (positions.avg_cost * positions.quantity + $4 * $3)
                                   / (positions.quantity + $3),
                        quantity = positions.quantity + $3,
                        updated_at = NOW()
                    """,
                    DEFAULT_USER_ID,
                    ticker,
                    quantity,
                    price,
                )

            elif side == "sell":
                # Check position exists and has enough shares
                row = await conn.fetchrow(
                    "SELECT quantity, avg_cost FROM positions WHERE user_id = $1 AND ticker = $2",
                    DEFAULT_USER_ID,
                    ticker,
                )
                if row is None or row["quantity"] < quantity:
                    held = row["quantity"] if row else 0
                    raise ValueError(
                        f"Insufficient shares: need {quantity}, have {held}"
                    )

                # Increase cash
                await conn.execute(
                    "UPDATE users_profile SET cash_balance = cash_balance + $1 WHERE user_id = $2",
                    total,
                    DEFAULT_USER_ID,
                )

                new_qty = row["quantity"] - quantity

                if abs(new_qty) < 1e-9:
                    # Delete position when fully sold (PORT-06)
                    await conn.execute(
                        "DELETE FROM positions WHERE user_id = $1 AND ticker = $2",
                        DEFAULT_USER_ID,
                        ticker,
                    )
                else:
                    # Partial sell: update quantity, avg_cost unchanged
                    await conn.execute(
                        "UPDATE positions SET quantity = $1, updated_at = NOW() WHERE user_id = $2 AND ticker = $3",
                        new_qty,
                        DEFAULT_USER_ID,
                        ticker,
                    )

            # 3. Log trade (PORT-07)
            await conn.execute(
                "INSERT INTO trades (user_id, ticker, side, quantity, price) VALUES ($1, $2, $3, $4, $5)",
                DEFAULT_USER_ID,
                ticker,
                side,
                quantity,
                price,
            )

    return {
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "total": total,
    }


async def get_portfolio(pool: Pool, price_cache: PriceCache) -> dict:
    """Get current portfolio state enriched with live prices.

    Returns a dict matching PortfolioResponse shape:
    - cash_balance: current cash
    - total_value: cash + sum of (current_price * quantity) for all positions
    - positions: list of PositionDetail dicts with unrealized P&L
    """
    async with pool.acquire() as conn:
        cash = await conn.fetchval(
            "SELECT cash_balance FROM users_profile WHERE user_id = $1",
            DEFAULT_USER_ID,
        )
        rows = await conn.fetch(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = $1",
            DEFAULT_USER_ID,
        )

    cash = cash or 0.0
    positions = []
    positions_value = 0.0

    for row in rows:
        current_price = price_cache.get_price(row["ticker"])
        qty = row["quantity"]
        avg = row["avg_cost"]

        # Use avg_cost as fallback if no live price available
        effective_price = current_price if current_price is not None else avg
        unrealized_pnl = round((effective_price - avg) * qty, 2)
        pnl_percent = round(((effective_price - avg) / avg) * 100, 2) if avg > 0 else 0.0

        if current_price is not None:
            positions_value += current_price * qty

        positions.append({
            "ticker": row["ticker"],
            "quantity": qty,
            "avg_cost": round(avg, 2),
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "pnl_percent": pnl_percent,
        })

    total_value = round(cash + positions_value, 2)

    return {
        "cash_balance": round(cash, 2),
        "total_value": total_value,
        "positions": positions,
    }


async def record_snapshot(pool: Pool, price_cache: PriceCache) -> None:
    """Record a portfolio value snapshot.

    Computes total_value = cash + sum(price * quantity) for all positions,
    then inserts into portfolio_snapshots. Called both after trades (PORT-09)
    and by the periodic background task (PORT-08, Plan 02-02).
    """
    async with pool.acquire() as conn:
        cash = await conn.fetchval(
            "SELECT cash_balance FROM users_profile WHERE user_id = $1",
            DEFAULT_USER_ID,
        )
        rows = await conn.fetch(
            "SELECT ticker, quantity FROM positions WHERE user_id = $1",
            DEFAULT_USER_ID,
        )

        positions_value = 0.0
        for row in rows:
            price = price_cache.get_price(row["ticker"])
            if price is not None:
                positions_value += price * row["quantity"]

        total_value = round((cash or 0.0) + positions_value, 2)

        await conn.execute(
            "INSERT INTO portfolio_snapshots (user_id, total_value) VALUES ($1, $2)",
            DEFAULT_USER_ID,
            total_value,
        )
