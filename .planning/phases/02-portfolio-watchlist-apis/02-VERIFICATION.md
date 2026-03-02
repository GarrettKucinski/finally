---
phase: 02-portfolio-watchlist-apis
verified: 2026-03-02T09:15:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
gaps: []
human_verification: []
---

# Phase 2: Portfolio & Watchlist APIs Verification Report

**Phase Goal:** Users can execute trades, view their portfolio with P&L, manage their watchlist, and the system records portfolio snapshots over time -- the core verbs of the trading platform
**Verified:** 2026-03-02T09:15:00Z
**Status:** PASSED
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

Plan 02-01 must_haves:

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GET /api/portfolio returns cash_balance, total_value, and positions array with per-position unrealized P&L | VERIFIED | `get_portfolio()` in `services/portfolio.py` queries cash + positions, enriches each with `price_cache.get_price()`, computes `unrealized_pnl` and `pnl_percent`; route at `routes/portfolio.py:22` returns result directly |
| 2  | POST /api/portfolio/trade executes a buy at the current cached price, decreasing cash and creating/updating a position | VERIFIED | `execute_trade()` line 44: `price_cache.get_price(ticker)`, lines 65-86: cash decrease + position upsert with ON CONFLICT weighted avg cost |
| 3  | POST /api/portfolio/trade executes a sell at the current cached price, increasing cash and updating/deleting a position | VERIFIED | `execute_trade()` lines 88-124: fetchrow for position, cash increase, new_qty update or DELETE |
| 4  | Buy with insufficient cash is rejected with 400 and ErrorResponse | VERIFIED | `execute_trade()` line 59: `raise ValueError("Insufficient cash...")`, route catches ValueError and returns `JSONResponse(status_code=400, content=ErrorResponse(...))` |
| 5  | Sell with insufficient shares is rejected with 400 and ErrorResponse | VERIFIED | `execute_trade()` lines 95-99: `raise ValueError("Insufficient shares...")`, same catch in route |
| 6  | Trade execution updates position + cash + trade log atomically in a single DB transaction | VERIFIED | `execute_trade()` lines 50-51: `async with pool.acquire() as conn:` + `async with conn.transaction():` wraps all mutations; test `test_trade_atomic` confirms |
| 7  | Position row is deleted when quantity reaches zero after a sell | VERIFIED | `execute_trade()` lines 110-116: `if abs(new_qty) < 1e-9: DELETE FROM positions`; test `test_sell_all_deletes_position` confirms |
| 8  | A portfolio snapshot is recorded immediately after each trade | VERIFIED | `routes/portfolio.py:53`: `await record_snapshot(pool, price_cache)` called after `execute_trade` succeeds, outside the transaction |
| 9  | GET /api/portfolio/history returns portfolio snapshots ordered by time | VERIFIED | `routes/portfolio_history.py:26-30`: SELECT with `ORDER BY recorded_at`; returns list of `{total_value, recorded_at}` |

Plan 02-02 must_haves:

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 10 | GET /api/watchlist returns all watched tickers with their latest prices from the price cache | VERIFIED | `services/watchlist.py:18-45`: fetches watchlist rows, enriches each with `price_cache.get(ticker)`, returns price/change/direction/added_at |
| 11 | POST /api/watchlist adds a valid ticker to the watchlist and registers it with the market data source | VERIFIED | `services/watchlist.py:48-65`: INSERT with ON CONFLICT DO NOTHING RETURNING id, then `source.add_ticker(ticker)` |
| 12 | POST /api/watchlist rejects invalid tickers (not 1-5 uppercase alpha) with 422 | VERIFIED | `models/watchlist.py:15-21`: `field_validator("ticker")` raises ValueError for non-alpha or len > 5; FastAPI returns 422; tests confirm |
| 13 | POST /api/watchlist returns 409 for duplicate tickers (idempotent DB insert) | VERIFIED | `services/watchlist.py:61-62`: `if result is None: raise ValueError("already in watchlist")`; route maps to 409; test `test_add_duplicate_ticker` confirms |
| 14 | DELETE /api/watchlist/{ticker} removes the ticker from the watchlist and unregisters it from the market data source | VERIFIED | `services/watchlist.py:68-85`: DELETE, check result string, then `source.remove_ticker(ticker)` |
| 15 | DELETE /api/watchlist/{ticker} returns 404 for tickers not in the watchlist | VERIFIED | `services/watchlist.py:81-82`: `if result == "DELETE 0": raise ValueError("not in watchlist")`; route returns 404; test `test_remove_nonexistent_ticker` confirms |
| 16 | Background task records a portfolio snapshot every 30 seconds | VERIFIED | `tasks/snapshots.py:23-30`: `while True` loop calling `record_snapshot(pool, price_cache)` then `asyncio.sleep(30)`; test `test_snapshot_recorder_loop` checks 30s sleep |
| 17 | Background task deletes portfolio snapshots older than 24 hours | VERIFIED | `tasks/snapshots.py:33-44`: DELETE WHERE `recorded_at < NOW() - INTERVAL '24 hours'`; test `test_snapshot_cleanup` verifies SQL |
| 18 | Background tasks are cancelled on shutdown without errors | VERIFIED | `main.py:90-98`: `snapshot_task.cancel()`, `cleanup_task.cancel()`, `await task` with `except asyncio.CancelledError: pass` BEFORE `source.stop()` and `close_db(pool)` |

**Score:** 18/18 truths verified

---

## Required Artifacts

### Plan 02-01 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/models/common.py` | VERIFIED | `ErrorResponse` class with `error: str` and `detail: str` fields -- 13 lines, substantive |
| `backend/app/models/portfolio.py` | VERIFIED | All 5 models present: `TradeRequest` (with 3 field_validators), `TradeResponse`, `PositionDetail`, `PortfolioResponse`, `SnapshotPoint` -- 79 lines |
| `backend/app/services/portfolio.py` | VERIFIED | All 3 functions: `execute_trade`, `get_portfolio`, `record_snapshot` -- 228 lines with full implementation |
| `backend/app/routes/portfolio.py` | VERIFIED | GET `/api/portfolio` and POST `/api/portfolio/trade` handlers, `router = APIRouter(tags=["portfolio"])` exported -- 60 lines |
| `backend/app/routes/portfolio_history.py` | VERIFIED | GET `/api/portfolio/history` handler, `router` exported -- 39 lines |
| `backend/tests/test_trade_service.py` | VERIFIED | 14 tests covering buy/sell/edge cases/atomicity/snapshot/get_portfolio -- 369 lines |
| `backend/tests/test_portfolio.py` | VERIFIED | 11 route-level tests covering all status codes and response shapes -- 303 lines |

### Plan 02-02 Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/models/watchlist.py` | VERIFIED | `AddTickerRequest` (with field_validator) and `WatchlistItem` models -- 33 lines |
| `backend/app/services/watchlist.py` | VERIFIED | `get_watchlist`, `add_ticker`, `remove_ticker` with DB + market source sync -- 86 lines |
| `backend/app/routes/watchlist.py` | VERIFIED | GET/POST/DELETE `/api/watchlist` handlers, `router` exported -- 70 lines |
| `backend/app/tasks/__init__.py` | VERIFIED | Package marker file exists |
| `backend/app/tasks/snapshots.py` | VERIFIED | `snapshot_recorder_loop` (30s) and `snapshot_cleanup_loop` (300s) -- 44 lines |
| `backend/tests/test_watchlist.py` | VERIFIED | 11 tests for watchlist routes and market source sync -- 285 lines |
| `backend/tests/test_snapshots.py` | VERIFIED | 5 tests for background tasks, error handling, intervals -- 150 lines |

---

## Key Link Verification

### Plan 02-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `routes/portfolio.py` | `services/portfolio.py` | `from app.services.portfolio import execute_trade, get_portfolio, record_snapshot` | WIRED | Line 17: exact import verified |
| `services/portfolio.py` | `market/cache.py` | `price_cache.get_price(ticker)` | WIRED | Lines 44, 168, 217: `get_price` called for fill price and portfolio valuation |
| `services/portfolio.py` | asyncpg pool | `conn.transaction()` | WIRED | Lines 50-51: `async with pool.acquire() as conn: async with conn.transaction():` |
| `main.py` | `routes/portfolio.py` | `app.include_router(portfolio_router)` | WIRED | Line 108: `app.include_router(portfolio_router)` |
| `main.py` | `routes/portfolio_history.py` | `app.include_router(portfolio_history_router)` | WIRED | Line 109: `app.include_router(portfolio_history_router)` |

### Plan 02-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `routes/watchlist.py` | `services/watchlist.py` | `from app.services.watchlist import get_watchlist, add_ticker, remove_ticker` | WIRED | Line 13: exact import verified |
| `services/watchlist.py` | `market/interface.py` | `source.add_ticker()` and `source.remove_ticker()` | WIRED | Lines 65 and 85: called after successful DB mutations |
| `tasks/snapshots.py` | `services/portfolio.py` | `from app.services.portfolio import record_snapshot` | WIRED | Line 18: import verified; line 27: called inside loop |
| `main.py` | `tasks/snapshots.py` | `asyncio.create_task(snapshot_recorder_loop(...))` | WIRED | Lines 84-85: both tasks created with `asyncio.create_task` |
| `main.py` | `routes/watchlist.py` | `app.include_router(watchlist_router)` | WIRED | Line 110: `app.include_router(watchlist_router)` |

---

## Requirements Coverage

All 16 requirement IDs declared across plans for this phase are satisfied:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PORT-01 | 02-01 | GET /api/portfolio returns positions, cash balance, total value, unrealized P&L | SATISFIED | `routes/portfolio.py` GET handler, `services/portfolio.py` `get_portfolio()` |
| PORT-02 | 02-01 | POST /api/portfolio/trade executes market order at current cached price | SATISFIED | `routes/portfolio.py` POST handler, `execute_trade()` with `price_cache.get_price()` |
| PORT-03 | 02-01 | Buy validation rejects when user has insufficient cash | SATISFIED | `execute_trade()` line 59: ValueError if `cash < total` |
| PORT-04 | 02-01 | Sell validation rejects when user has insufficient shares | SATISFIED | `execute_trade()` line 95-99: ValueError if `row is None or row["quantity"] < quantity` |
| PORT-05 | 02-01 | Trade execution updates positions and cash atomically within DB transaction | SATISFIED | `conn.transaction()` context wraps all mutations |
| PORT-06 | 02-01 | Position row deleted when quantity reaches 0 after sell | SATISFIED | `execute_trade()` lines 110-116: `DELETE FROM positions` when `abs(new_qty) < 1e-9` |
| PORT-07 | 02-01 | Trade history appended to trades table on every execution | SATISFIED | `execute_trade()` lines 127-134: `INSERT INTO trades` with user_id, ticker, side, quantity, price |
| PORT-08 | 02-02 | Background task records portfolio value snapshot every 30 seconds | SATISFIED | `tasks/snapshots.py` `snapshot_recorder_loop` with 30s sleep; `main.py` create_task |
| PORT-09 | 02-01 | Portfolio snapshot recorded immediately after each trade | SATISFIED | `routes/portfolio.py:53`: `await record_snapshot(pool, price_cache)` after `execute_trade` |
| PORT-10 | 02-02 | Background task deletes portfolio snapshots older than 24 hours | SATISFIED | `tasks/snapshots.py` `snapshot_cleanup_loop`: DELETE with `INTERVAL '24 hours'`, 300s sleep |
| PORT-11 | 02-01 | GET /api/portfolio/history returns portfolio value snapshots over time | SATISFIED | `routes/portfolio_history.py` GET handler with ORDER BY recorded_at |
| WATCH-01 | 02-02 | GET /api/watchlist returns current watchlist tickers with latest prices | SATISFIED | `routes/watchlist.py` GET handler, `services/watchlist.py` `get_watchlist()` |
| WATCH-02 | 02-02 | POST /api/watchlist adds ticker (validated: 1-5 uppercase alpha) | SATISFIED | `models/watchlist.py` field_validator, `services/watchlist.py` `add_ticker()` |
| WATCH-03 | 02-02 | DELETE /api/watchlist/{ticker} removes ticker | SATISFIED | `routes/watchlist.py` DELETE handler, `services/watchlist.py` `remove_ticker()` |
| WATCH-04 | 02-02 | Adding watchlist ticker registers it with live market data source | SATISFIED | `services/watchlist.py:65`: `await source.add_ticker(ticker)` after successful DB insert |
| WATCH-05 | 02-02 | Removing watchlist ticker unregisters it from market data source | SATISFIED | `services/watchlist.py:85`: `await source.remove_ticker(ticker)` after successful DELETE |

**Orphaned requirements check:** REQUIREMENTS.md traceability table maps PORT-01 through PORT-11 and WATCH-01 through WATCH-05 all to Phase 2. All 16 are claimed by the two plans. No orphaned requirements.

---

## Test Suite Results

Full test run confirms:

- **Phase 2 tests:** 41/41 passed (14 service + 11 portfolio routes + 11 watchlist + 5 snapshots)
- **Full test suite:** 171/171 passed (zero regressions against Phase 1 tests)

---

## Anti-Patterns Found

No anti-patterns found in Phase 2 implementation files:

- No TODO/FIXME/PLACEHOLDER comments in `backend/app/` files
- No stub implementations (no `return null`, `return {}`, `return []`, unimplemented functions)
- The only `pass` in `main.py` is inside `except asyncio.CancelledError:` -- correct pattern for task cancellation
- `pass` in `market/` files (simulator, stream, massive_client) are from Phase 1 and are not part of this phase's scope

---

## Human Verification Required

None. All observable behaviors for this phase are verifiable programmatically:

- API response shapes: verified via test mocks
- Atomic transactions: verified via `test_trade_atomic` test
- Market source sync: verified via `test_add_registers_market_source` and `test_remove_unregisters_market_source`
- Background task intervals: verified via mocked `asyncio.sleep` assertions
- Error handling: verified via specific ValueError/status code tests

No visual UI, real-time behavior, or external service integration to verify in this phase (backend-only).

---

## Summary

Phase 2 achieves its stated goal: the core trading verbs of the platform are fully implemented and tested. Users (via the API) can:

1. **View their portfolio** with live-price-enriched positions and computed unrealized P&L (PORT-01)
2. **Execute trades** with atomic DB transactions, weighted average cost, and instant fill at cached price (PORT-02 through PORT-07)
3. **Track portfolio value over time** via automatic snapshot recording after each trade and every 30 seconds (PORT-08, PORT-09, PORT-11)
4. **Manage their watchlist** with automatic market data source sync so SSE streaming stays in sync (WATCH-01 through WATCH-05)
5. **Benefit from automatic data hygiene** via the 24-hour snapshot cleanup background task (PORT-10)

All 18 observable truths verified. All 16 requirements satisfied. 171 tests pass with no regressions.

---

_Verified: 2026-03-02T09:15:00Z_
_Verifier: Claude (gsd-verifier)_
