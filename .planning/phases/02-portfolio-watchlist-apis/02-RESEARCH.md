# Phase 2: Portfolio & Watchlist APIs - Research

**Researched:** 2026-03-02
**Domain:** FastAPI CRUD routes, asyncpg transactions, background tasks (asyncio.create_task), portfolio math, ticker validation
**Confidence:** HIGH

## Summary

Phase 2 adds the core trading functionality to FinAlly: portfolio management (view positions, execute trades, track P&L), watchlist CRUD (add/remove tickers with market data source integration), and background snapshot tasks (periodic recording + cleanup). This builds directly on Phase 1's database foundation (asyncpg pool, 7 tables, seed data) and the existing market data subsystem (PriceCache, MarketDataSource with add_ticker/remove_ticker).

The phase is entirely backend Python work -- no frontend, no LLM, no new dependencies. All 16 requirements (PORT-01 through PORT-11, WATCH-01 through WATCH-05) are FastAPI route handlers backed by asyncpg queries against the existing schema. The critical technical patterns are: (1) atomic trade execution using asyncpg `conn.transaction()` context manager to update positions + cash + trade log in a single transaction, (2) two long-running background tasks launched via `asyncio.create_task()` in the FastAPI lifespan (snapshot recorder every 30s, cleanup task for records older than 24h), and (3) watchlist endpoints that both modify the database AND call `source.add_ticker()` / `source.remove_ticker()` to keep the live price stream in sync.

No new Python dependencies are needed. The existing stack (FastAPI 0.135.1, asyncpg 0.31.0, Pydantic 2.x) provides everything required. The `httpx` library already in pyproject.toml is used for route testing via `httpx.ASGITransport`. All prices come from the existing `PriceCache` (accessed via `request.app.state.price_cache`), and the market data source is accessed via `request.app.state.market_source`.

**Primary recommendation:** Create three new route modules (`routes/portfolio.py`, `routes/watchlist.py`, `routes/portfolio_history.py`) with Pydantic request/response models, a `services/portfolio.py` module for trade execution logic (keeps routes thin), and two background tasks launched in the lifespan. Use the established pattern from Phase 1: routers export a `router` object, registered via `app.include_router()` in `main.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PORT-01 | `GET /api/portfolio` returns current positions, cash balance, total portfolio value, and unrealized P&L per position | Query `positions` + `users_profile` tables; enrich with live prices from `PriceCache.get_price()`; compute unrealized P&L as `(current_price - avg_cost) * quantity` |
| PORT-02 | `POST /api/portfolio/trade` executes a market order (buy or sell) at the current cached price with instant fill | Read fill price from `PriceCache.get_price(ticker)`; validate cash/shares; execute within `conn.transaction()` |
| PORT-03 | Buy validation rejects trades when user has insufficient cash | Check `cash_balance >= price * quantity` before executing; return 400 with error model |
| PORT-04 | Sell validation rejects trades when user has insufficient shares | Check existing position quantity >= sell quantity; return 400 with error model |
| PORT-05 | Trade execution updates positions (upsert) and cash balance atomically within a DB transaction | asyncpg `async with conn.transaction():` wraps position upsert + cash update + trade log insert |
| PORT-06 | Position row is deleted when quantity reaches 0 after a sell | After sell, check if new quantity == 0; if so, `DELETE FROM positions WHERE ...` instead of UPDATE |
| PORT-07 | Trade history is appended to the trades table on every execution | `INSERT INTO trades (user_id, ticker, side, quantity, price)` inside the transaction |
| PORT-08 | Background task records portfolio value snapshot every 30 seconds | `asyncio.create_task()` launched in lifespan; queries positions + cash + prices; inserts into `portfolio_snapshots` |
| PORT-09 | Portfolio snapshot is recorded immediately after each trade execution | After trade transaction commits, call snapshot function directly (same logic as periodic task) |
| PORT-10 | Background task deletes portfolio snapshots older than 24 hours | Second `asyncio.create_task()` in lifespan; runs `DELETE FROM portfolio_snapshots WHERE recorded_at < NOW() - INTERVAL '24 hours'`; runs every ~5 minutes |
| PORT-11 | `GET /api/portfolio/history` returns portfolio value snapshots over time | Simple `SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = $1 ORDER BY recorded_at` |
| WATCH-01 | `GET /api/watchlist` returns current watchlist tickers with latest prices from the price cache | Query `watchlist` table; for each ticker, call `PriceCache.get(ticker)` to enrich with live price data |
| WATCH-02 | `POST /api/watchlist` adds a ticker to the watchlist (validated: 1-5 uppercase alpha characters) | Pydantic model with `ticker: str` + validator (strip, uppercase, regex `^[A-Z]{1,5}$`); INSERT with ON CONFLICT for idempotency |
| WATCH-03 | `DELETE /api/watchlist/{ticker}` removes a ticker from the watchlist | `DELETE FROM watchlist WHERE user_id = $1 AND ticker = $2`; return 404 if not found |
| WATCH-04 | Adding a watchlist ticker also registers it with the live market data source | After DB insert, call `await request.app.state.market_source.add_ticker(ticker)` |
| WATCH-05 | Removing a watchlist ticker also unregisters it from the live market data source | After DB delete, call `await request.app.state.market_source.remove_ticker(ticker)` |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | Route handlers, APIRouter, Request object, HTTPException | Already installed; established pattern from Phase 1 health endpoint |
| asyncpg | 0.31.0 | All database queries, connection pool, transactions | Already installed; `conn.transaction()` provides atomic multi-statement execution |
| Pydantic | 2.x | Request/response models, field validators, error serialization | Already installed (transitive); `model_validator` and `field_validator` for ticker validation |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.27.0+ | Testing route handlers via `ASGITransport` | Already installed; established test pattern from Phase 1 `test_health.py` |
| pytest-asyncio | 0.24.0+ | Async test support | Already installed; `asyncio_mode = "auto"` in pyproject.toml |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw asyncpg transactions | SQLAlchemy async sessions | ORM adds complexity; project uses raw SQL throughout; schema is simple |
| `asyncio.create_task()` for background tasks | APScheduler or Celery | Massive overkill for two simple periodic tasks; adds dependency; asyncio is built-in |
| FastAPI `BackgroundTasks` for snapshots | `asyncio.create_task()` in lifespan | `BackgroundTasks` runs per-request, not perpetually; wrong tool for a 30-second recurring task |

**Installation:** No new dependencies needed -- everything is already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── main.py                  # UPDATE: register new routers + launch background tasks in lifespan
├── config.py                # (unchanged)
├── db.py                    # (unchanged)
├── models/                  # NEW: Pydantic request/response models
│   ├── __init__.py
│   ├── portfolio.py         # PortfolioResponse, TradeRequest, TradeResponse, PositionDetail
│   ├── watchlist.py         # WatchlistItem, AddTickerRequest
│   └── common.py            # ErrorResponse model (reusable across all routes)
├── services/                # NEW: Business logic layer
│   ├── __init__.py
│   ├── portfolio.py         # execute_trade(), get_portfolio(), record_snapshot()
│   └── watchlist.py         # add_ticker(), remove_ticker(), get_watchlist()
├── routes/
│   ├── __init__.py          # (unchanged)
│   ├── health.py            # (unchanged)
│   ├── portfolio.py         # NEW: GET /api/portfolio, POST /api/portfolio/trade
│   ├── portfolio_history.py # NEW: GET /api/portfolio/history
│   └── watchlist.py         # NEW: GET/POST/DELETE /api/watchlist
├── tasks/                   # NEW: Background tasks
│   ├── __init__.py
│   └── snapshots.py         # snapshot_recorder_loop(), snapshot_cleanup_loop()
├── market/                  # (unchanged -- just consumed via app.state)
└── schema/                  # (unchanged)
```

### Pattern 1: Service Layer for Trade Execution

**What:** Separate business logic (trade validation, execution, P&L calculation) from route handlers. Routes handle HTTP concerns (request parsing, response formatting, error codes); services handle domain logic (validation, DB operations, side effects).

**When to use:** Whenever a route handler would be more than ~15 lines of logic. Trade execution involves validation, multiple DB operations, and a snapshot side-effect -- too complex for inline route code.

**Example:**
```python
# services/portfolio.py
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
    """Execute a trade atomically. Returns trade details or raises ValueError."""
    price = price_cache.get_price(ticker)
    if price is None:
        raise ValueError(f"No price available for {ticker}")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Read current cash
            cash = await conn.fetchval(
                "SELECT cash_balance FROM users_profile WHERE user_id = $1",
                DEFAULT_USER_ID,
            )

            if side == "buy":
                cost = price * quantity
                if cash < cost:
                    raise ValueError(f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}")
                # Update cash
                await conn.execute(
                    "UPDATE users_profile SET cash_balance = cash_balance - $1 WHERE user_id = $2",
                    cost, DEFAULT_USER_ID,
                )
                # Upsert position
                await conn.execute("""
                    INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (user_id, ticker) DO UPDATE SET
                        avg_cost = (positions.avg_cost * positions.quantity + $4 * $3)
                                   / (positions.quantity + $3),
                        quantity = positions.quantity + $3,
                        updated_at = NOW()
                """, DEFAULT_USER_ID, ticker, quantity, price)
            elif side == "sell":
                # Check position exists and has enough shares
                row = await conn.fetchrow(
                    "SELECT quantity, avg_cost FROM positions WHERE user_id = $1 AND ticker = $2",
                    DEFAULT_USER_ID, ticker,
                )
                if row is None or row["quantity"] < quantity:
                    held = row["quantity"] if row else 0
                    raise ValueError(f"Insufficient shares: need {quantity}, have {held}")

                proceeds = price * quantity
                new_qty = row["quantity"] - quantity

                # Update cash
                await conn.execute(
                    "UPDATE users_profile SET cash_balance = cash_balance + $1 WHERE user_id = $2",
                    proceeds, DEFAULT_USER_ID,
                )

                if new_qty == 0:
                    # Delete position when fully sold (PORT-06)
                    await conn.execute(
                        "DELETE FROM positions WHERE user_id = $1 AND ticker = $2",
                        DEFAULT_USER_ID, ticker,
                    )
                else:
                    await conn.execute(
                        "UPDATE positions SET quantity = $1, updated_at = NOW() WHERE user_id = $2 AND ticker = $3",
                        new_qty, DEFAULT_USER_ID, ticker,
                    )

            # 3. Log trade (PORT-07)
            await conn.execute(
                "INSERT INTO trades (user_id, ticker, side, quantity, price) VALUES ($1, $2, $3, $4, $5)",
                DEFAULT_USER_ID, ticker, side, quantity, price,
            )

    return {"ticker": ticker, "side": side, "quantity": quantity, "price": price}
```

### Pattern 2: Background Tasks via asyncio.create_task() in Lifespan

**What:** Long-running periodic tasks launched in the FastAPI lifespan, cancelled on shutdown. NOT the same as FastAPI's `BackgroundTasks` (which is per-request).

**When to use:** For the 30-second snapshot recorder (PORT-08) and the 24-hour cleanup task (PORT-10).

**Example:**
```python
# tasks/snapshots.py
import asyncio
import logging
from asyncpg import Pool
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

async def record_snapshot(pool: Pool, price_cache: PriceCache) -> None:
    """Record a single portfolio value snapshot. Used by both periodic task and post-trade."""
    async with pool.acquire() as conn:
        # Get cash balance
        cash = await conn.fetchval(
            "SELECT cash_balance FROM users_profile WHERE user_id = $1",
            DEFAULT_USER_ID,
        )
        # Get positions
        rows = await conn.fetch(
            "SELECT ticker, quantity FROM positions WHERE user_id = $1",
            DEFAULT_USER_ID,
        )
        # Calculate total value
        positions_value = 0.0
        for row in rows:
            price = price_cache.get_price(row["ticker"])
            if price is not None:
                positions_value += price * row["quantity"]

        total_value = (cash or 0.0) + positions_value

        await conn.execute(
            "INSERT INTO portfolio_snapshots (user_id, total_value) VALUES ($1, $2)",
            DEFAULT_USER_ID, total_value,
        )

async def snapshot_recorder_loop(pool: Pool, price_cache: PriceCache) -> None:
    """Record portfolio snapshot every 30 seconds. Runs until cancelled."""
    while True:
        try:
            await record_snapshot(pool, price_cache)
        except Exception:
            logger.exception("Failed to record portfolio snapshot")
        await asyncio.sleep(30)

async def snapshot_cleanup_loop(pool: Pool) -> None:
    """Delete portfolio snapshots older than 24 hours. Runs every 5 minutes."""
    while True:
        try:
            async with pool.acquire() as conn:
                deleted = await conn.execute(
                    "DELETE FROM portfolio_snapshots WHERE recorded_at < NOW() - INTERVAL '24 hours'"
                )
                logger.debug("Snapshot cleanup: %s", deleted)
        except Exception:
            logger.exception("Failed to clean up portfolio snapshots")
        await asyncio.sleep(300)  # 5 minutes
```

```python
# In main.py lifespan (addition):
snapshot_task = asyncio.create_task(snapshot_recorder_loop(pool, cache))
cleanup_task = asyncio.create_task(snapshot_cleanup_loop(pool))

yield  # app runs

# Shutdown
snapshot_task.cancel()
cleanup_task.cancel()
# Await cancellation to avoid warnings
try:
    await snapshot_task
except asyncio.CancelledError:
    pass
try:
    await cleanup_task
except asyncio.CancelledError:
    pass
```

### Pattern 3: Pydantic Models for Request/Response Validation

**What:** Typed Pydantic models for all API inputs and outputs, including a shared `ErrorResponse` model.

**When to use:** Every endpoint. Ensures consistent error format, auto-generates OpenAPI docs, validates input automatically.

**Example:**
```python
# models/portfolio.py
from pydantic import BaseModel, field_validator

class TradeRequest(BaseModel):
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or not (1 <= len(v) <= 5):
            raise ValueError("Ticker must be 1-5 uppercase alpha characters")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("buy", "sell"):
            raise ValueError("Side must be 'buy' or 'sell'")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

class PositionDetail(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None
    unrealized_pnl: float
    pnl_percent: float

class PortfolioResponse(BaseModel):
    cash_balance: float
    total_value: float
    positions: list[PositionDetail]

class TradeResponse(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float
    total: float

# models/common.py
class ErrorResponse(BaseModel):
    error: str
    detail: str
```

### Pattern 4: Watchlist with Market Data Source Sync

**What:** Watchlist endpoints that both persist to DB and register/unregister tickers with the live market data source.

**When to use:** `POST /api/watchlist` and `DELETE /api/watchlist/{ticker}` (WATCH-04, WATCH-05).

**Example:**
```python
# routes/watchlist.py
@router.post("/api/watchlist", status_code=201)
async def add_ticker(request: Request, body: AddTickerRequest):
    pool = request.app.state.db_pool
    source = request.app.state.market_source

    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO watchlist (user_id, ticker) VALUES ($1, $2)",
                DEFAULT_USER_ID, body.ticker,
            )
        except asyncpg.UniqueViolationError:
            return JSONResponse(
                status_code=409,
                content={"error": "Duplicate", "detail": f"{body.ticker} already in watchlist"},
            )

    # Register with market data source so prices start streaming (WATCH-04)
    await source.add_ticker(body.ticker)

    return {"ticker": body.ticker, "status": "added"}


@router.delete("/api/watchlist/{ticker}")
async def remove_ticker(request: Request, ticker: str):
    pool = request.app.state.db_pool
    source = request.app.state.market_source

    ticker = ticker.strip().upper()

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM watchlist WHERE user_id = $1 AND ticker = $2",
            DEFAULT_USER_ID, ticker,
        )

    if result == "DELETE 0":
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "detail": f"{ticker} not in watchlist"},
        )

    # Unregister from market data source (WATCH-05)
    await source.remove_ticker(ticker)

    return {"ticker": ticker, "status": "removed"}
```

### Anti-Patterns to Avoid

- **Putting business logic in route handlers:** Trade execution involves 5+ DB operations plus validation. Inline code makes routes untestable and hard to reuse (the chat endpoint in Phase 3 reuses `execute_trade`). Use a service layer.
- **Using `BackgroundTasks` for periodic work:** FastAPI's `BackgroundTasks` runs once per request. The snapshot recorder needs to run every 30 seconds regardless of requests. Use `asyncio.create_task()` in the lifespan instead.
- **Non-atomic trade execution:** If position update succeeds but cash update fails, the system is in an inconsistent state. Always wrap in `async with conn.transaction()`.
- **Forgetting to sync watchlist with market source:** Adding a ticker to the DB without calling `source.add_ticker()` means no prices will stream for it. Both steps must happen together.
- **Using float equality for zero-quantity check:** After subtraction, check `new_qty <= 0` or use an epsilon comparison. In practice, since both quantities come from the DB as floats, exact equality works, but prefer `abs(new_qty) < 1e-9` for safety.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation | Manual if/else checks on request body | Pydantic `BaseModel` with `field_validator` | Automatic 422 errors, type coercion, OpenAPI docs generation |
| Transaction atomicity | Manual BEGIN/COMMIT/ROLLBACK | asyncpg `async with conn.transaction()` | Automatic rollback on exception, nested savepoint support |
| Error response format | Ad-hoc dict construction | Pydantic `ErrorResponse` model | Consistent `{"error": "...", "detail": "..."}` across all endpoints |
| Async background loops | Threading or `schedule` library | `asyncio.create_task()` with `while True` + `asyncio.sleep()` | Native to the event loop; proper cancellation via `task.cancel()` |
| Average cost calculation | Application-level read-modify-write | SQL `ON CONFLICT DO UPDATE SET avg_cost = ...` expression | Single atomic operation; no race condition between concurrent trades |

**Key insight:** The asyncpg `conn.transaction()` context manager and Pydantic validators handle 90% of the complexity in this phase. Trade execution is the hardest part, but it's a well-understood pattern: read-validate-mutate inside a transaction.

## Common Pitfalls

### Pitfall 1: Average Cost Calculation on Buy Upsert

**What goes wrong:** Incorrect weighted average cost when buying additional shares of an existing position. The formula `(old_avg * old_qty + new_price * new_qty) / (old_qty + new_qty)` is easy to get wrong in SQL.

**Why it happens:** The SQL `ON CONFLICT DO UPDATE` clause needs to reference both the existing row values (`positions.quantity`, `positions.avg_cost`) and the new values being inserted (`EXCLUDED.*` or the dollar-sign params).

**How to avoid:** Use `positions.avg_cost` and `positions.quantity` (the table-qualified names) to reference current values in the `ON CONFLICT DO UPDATE SET` clause. Test with: buy 10 shares at $100, then buy 5 more at $200, verify avg_cost = $133.33.

**Warning signs:** avg_cost shows the latest trade price instead of a weighted average.

### Pitfall 2: asyncpg DELETE Returns Status String, Not Row Count

**What goes wrong:** Checking `result == 0` after `conn.execute("DELETE ...")` fails because asyncpg's `execute()` returns a status string like `"DELETE 0"` or `"DELETE 1"`, not an integer.

**Why it happens:** asyncpg's `execute()` returns the PostgreSQL command tag as a string. This is unlike ORMs that return affected row counts as integers.

**How to avoid:** Parse the status string: `result == "DELETE 0"` means no rows deleted (404). Or use `conn.fetchrow("DELETE ... RETURNING id")` and check if the result is `None`.

**Warning signs:** Deleting a non-existent ticker returns 200 instead of 404.

### Pitfall 3: Forgetting to Cancel Background Tasks on Shutdown

**What goes wrong:** Background tasks continue running after the FastAPI lifespan exits, causing "event loop is closed" errors or database pool access after close.

**Why it happens:** `asyncio.create_task()` creates fire-and-forget tasks. They must be explicitly cancelled in the lifespan's shutdown code (after `yield`).

**How to avoid:** Store task references, call `task.cancel()` in the shutdown section, and `await` the tasks with a try/except for `CancelledError`.

**Warning signs:** Warnings about pending tasks or database pool errors on shutdown.

### Pitfall 4: Floating Point Precision in Cash Balance

**What goes wrong:** After many buy/sell cycles, cash balance drifts due to floating-point arithmetic (e.g., $9999.999999999998 instead of $10000.00).

**Why it happens:** `DOUBLE PRECISION` in Postgres and Python `float` both use IEEE 754 binary floating point. Repeated add/subtract introduces tiny errors.

**How to avoid:** Round cash amounts to 2 decimal places in the service layer before DB operations: `cost = round(price * quantity, 2)`. The schema uses `DOUBLE PRECISION` (not `NUMERIC`), so application-level rounding is the mitigation.

**Warning signs:** Portfolio display shows cash like `$9,999.999999998` instead of clean dollars and cents.

### Pitfall 5: Race Condition Between Trade and Snapshot

**What goes wrong:** The periodic snapshot task reads portfolio state while a trade is mid-transaction, seeing partially updated data.

**Why it happens:** The snapshot query and the trade transaction acquire separate connections from the pool. Postgres snapshot isolation protects each connection but they see different points in time.

**How to avoid:** This is acceptable for periodic snapshots (30-second granularity makes sub-second inconsistency negligible). For the post-trade snapshot (PORT-09), call `record_snapshot()` AFTER the trade transaction commits, ensuring it sees the committed state.

**Warning signs:** Snapshot total_value occasionally doesn't match expected post-trade value. This is inherent to the design and acceptable.

## Code Examples

### Trade Execution with Atomic Transaction
```python
# Source: asyncpg documentation + project pattern
async with pool.acquire() as conn:
    async with conn.transaction():
        # All operations here are atomic
        cash = await conn.fetchval(
            "SELECT cash_balance FROM users_profile WHERE user_id = $1",
            user_id,
        )
        # ... validation ...
        await conn.execute(
            "UPDATE users_profile SET cash_balance = cash_balance - $1 WHERE user_id = $2",
            cost, user_id,
        )
        await conn.execute("""
            INSERT INTO positions (user_id, ticker, quantity, avg_cost)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, ticker) DO UPDATE SET
                avg_cost = (positions.avg_cost * positions.quantity + $4 * $3)
                           / (positions.quantity + $3),
                quantity = positions.quantity + $3,
                updated_at = NOW()
        """, user_id, ticker, quantity, price)
        await conn.execute(
            "INSERT INTO trades (user_id, ticker, side, quantity, price) VALUES ($1, $2, $3, $4, $5)",
            user_id, ticker, "buy", quantity, price,
        )
        # Transaction auto-commits when the `async with` block exits normally
        # Auto-rolls back if any exception is raised
```

### Portfolio P&L Calculation
```python
# Source: project requirements + PriceCache API
async def get_portfolio(pool: Pool, price_cache: PriceCache) -> dict:
    async with pool.acquire() as conn:
        cash = await conn.fetchval(
            "SELECT cash_balance FROM users_profile WHERE user_id = $1",
            DEFAULT_USER_ID,
        )
        rows = await conn.fetch(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = $1",
            DEFAULT_USER_ID,
        )

    positions = []
    positions_value = 0.0
    for row in rows:
        current_price = price_cache.get_price(row["ticker"])
        qty = row["quantity"]
        avg = row["avg_cost"]
        unrealized_pnl = ((current_price or avg) - avg) * qty
        pnl_pct = ((current_price or avg) - avg) / avg * 100 if avg > 0 else 0.0
        if current_price is not None:
            positions_value += current_price * qty

        positions.append({
            "ticker": row["ticker"],
            "quantity": qty,
            "avg_cost": round(avg, 2),
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
        })

    total_value = (cash or 0.0) + positions_value
    return {
        "cash_balance": round(cash or 0.0, 2),
        "total_value": round(total_value, 2),
        "positions": positions,
    }
```

### Ticker Validation with Pydantic
```python
# Source: Pydantic v2 docs + project decisions (Q2 from PLAN.md)
from pydantic import BaseModel, field_validator

class AddTickerRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalpha() or not (1 <= len(v) <= 5):
            raise ValueError("Ticker must be 1-5 uppercase alpha characters")
        return v
```

### Testing Route Handlers (established pattern from Phase 1)
```python
# Source: backend/tests/test_health.py pattern
import httpx
from app.main import app

async def test_get_portfolio(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")

    # Mock app.state dependencies
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    conn.fetchval = AsyncMock(return_value=10000.0)  # cash balance
    conn.fetch = AsyncMock(return_value=[])  # no positions

    price_cache = PriceCache()
    app.state.db_pool = pool
    app.state.price_cache = price_cache

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/portfolio")

    assert response.status_code == 200
    data = response.json()
    assert data["cash_balance"] == 10000.0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `on_startup`/`on_shutdown` events | `lifespan` async context manager | FastAPI 0.100+ (2023) | Background tasks launched in lifespan, not in deprecated events |
| Pydantic v1 validators | Pydantic v2 `field_validator` with `@classmethod` | Pydantic 2.0 (2023) | New decorator syntax; `@validator` is deprecated |
| `asyncpg.connect()` per request | `asyncpg.create_pool()` shared pool | Always (best practice) | Pool already created in Phase 1; routes acquire from pool |

**Deprecated/outdated:**
- `@validator` decorator in Pydantic: replaced by `@field_validator` in Pydantic v2
- FastAPI `on_startup`/`on_shutdown`: replaced by `lifespan` context manager
- `response_model` parameter on routes: still works but `-> ReturnType` annotation is now preferred

## Open Questions

1. **Should the sell avg_cost be preserved when partially selling?**
   - What we know: When selling part of a position, the avg_cost stays the same (only quantity changes). This is standard FIFO-equivalent behavior for average cost basis.
   - What's unclear: Nothing -- this is the standard approach.
   - Recommendation: Keep avg_cost unchanged on partial sells; only quantity decreases.

2. **Should POST /api/watchlist return the full watchlist or just the added ticker?**
   - What we know: PLAN.md doesn't specify the response shape for POST.
   - What's unclear: Whether returning just `{ticker, status: "added"}` or the full updated watchlist is better for the frontend.
   - Recommendation: Return `{ticker, status: "added"}` for simplicity. Frontend can refetch the full watchlist if needed. This matches REST convention (return the created resource, not the collection).

3. **Should there be a check preventing selling a ticker not on the watchlist?**
   - What we know: The PLAN says the user can trade any ticker (not just watchlisted ones). Positions table is independent of watchlist.
   - What's unclear: Nothing.
   - Recommendation: Allow trading any ticker that has a price in the cache. Watchlist and positions are independent concepts.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `cd backend && uv run pytest tests/ -x -q` |
| Full suite command | `cd backend && uv run pytest tests/ -v --cov=app` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | GET /api/portfolio returns positions, cash, total value, unrealized P&L | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_empty -x` | Wave 0 |
| PORT-01 | GET /api/portfolio with positions and live prices | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_with_positions -x` | Wave 0 |
| PORT-02 | POST /api/portfolio/trade executes buy at cached price | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_execute_buy -x` | Wave 0 |
| PORT-02 | POST /api/portfolio/trade executes sell at cached price | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_execute_sell -x` | Wave 0 |
| PORT-03 | Buy with insufficient cash returns 400 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_buy_insufficient_cash -x` | Wave 0 |
| PORT-04 | Sell with insufficient shares returns 400 | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_sell_insufficient_shares -x` | Wave 0 |
| PORT-05 | Trade updates position + cash atomically (transaction) | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_trade_atomic -x` | Wave 0 |
| PORT-06 | Selling all shares deletes position row | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_sell_all_deletes_position -x` | Wave 0 |
| PORT-07 | Trade appends to trades table | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_trade_creates_log_entry -x` | Wave 0 |
| PORT-08 | Background task records snapshot every 30s | unit | `cd backend && uv run pytest tests/test_snapshots.py::test_snapshot_recorder_loop -x` | Wave 0 |
| PORT-09 | Snapshot recorded after trade | unit | `cd backend && uv run pytest tests/test_trade_service.py::test_snapshot_after_trade -x` | Wave 0 |
| PORT-10 | Background task deletes old snapshots | unit | `cd backend && uv run pytest tests/test_snapshots.py::test_snapshot_cleanup -x` | Wave 0 |
| PORT-11 | GET /api/portfolio/history returns snapshots | unit | `cd backend && uv run pytest tests/test_portfolio.py::test_get_portfolio_history -x` | Wave 0 |
| WATCH-01 | GET /api/watchlist returns tickers with prices | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_get_watchlist -x` | Wave 0 |
| WATCH-02 | POST /api/watchlist adds valid ticker | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_ticker -x` | Wave 0 |
| WATCH-02 | POST /api/watchlist rejects invalid ticker | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_invalid_ticker -x` | Wave 0 |
| WATCH-03 | DELETE /api/watchlist/{ticker} removes ticker | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_ticker -x` | Wave 0 |
| WATCH-03 | DELETE /api/watchlist/{ticker} returns 404 for unknown | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_nonexistent_ticker -x` | Wave 0 |
| WATCH-04 | Adding ticker registers with market source | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_add_registers_market_source -x` | Wave 0 |
| WATCH-05 | Removing ticker unregisters from market source | unit | `cd backend && uv run pytest tests/test_watchlist.py::test_remove_unregisters_market_source -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/ -x -q`
- **Per wave merge:** `cd backend && uv run pytest tests/ -v --cov=app`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_portfolio.py` -- covers PORT-01, PORT-02, PORT-03, PORT-04, PORT-11
- [ ] `tests/test_trade_service.py` -- covers PORT-05, PORT-06, PORT-07, PORT-09
- [ ] `tests/test_snapshots.py` -- covers PORT-08, PORT-10
- [ ] `tests/test_watchlist.py` -- covers WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05

## Sources

### Primary (HIGH confidence)

- Context7 `/magicstack/asyncpg` -- transaction management, INSERT ON CONFLICT, fetchval/fetchrow/fetch, pool.acquire patterns
- Context7 `/websites/fastapi_tiangolo` -- lifespan context manager, BackgroundTasks (and why NOT to use for periodic tasks), HTTPException, APIRouter
- Existing codebase: `backend/app/main.py`, `backend/app/market/cache.py`, `backend/app/market/interface.py` -- established patterns for app.state, PriceCache API, MarketDataSource.add_ticker/remove_ticker
- Existing codebase: `backend/tests/test_health.py` -- established test pattern with httpx.ASGITransport + AsyncMock

### Secondary (MEDIUM confidence)

- PLAN.md sections 7 (Database schema), 8 (API endpoints), 13 (Decisions log) -- authoritative project specification
- Planning decisions: Q3 (delete zero positions), Q7 (fill at cache price), Q8 (error format), N5 (fractional shares)

### Tertiary (LOW confidence)

- None. All findings are verified against existing code or official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in Phase 1; no new dependencies
- Architecture: HIGH -- patterns directly extend Phase 1's established structure (routes, app.state, tests)
- Pitfalls: HIGH -- transaction patterns and asyncpg behavior verified via Context7 documentation; float precision is well-known
- Validation: HIGH -- test framework already configured and working (130 tests passing)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (30 days -- stable stack, no fast-moving dependencies)
