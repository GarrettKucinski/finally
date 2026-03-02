---
phase: 02-portfolio-watchlist-apis
plan: 01
subsystem: api
tags: [fastapi, asyncpg, pydantic, portfolio, trade-execution, transactions, sse]

requires:
  - phase: 01-database-foundation plan 01
    provides: asyncpg pool on app.state.db_pool, schema with positions/trades/users_profile/portfolio_snapshots tables
  - phase: 01-database-foundation plan 02
    provides: Routes package structure, router registration pattern, health endpoint pattern
provides:
  - ErrorResponse Pydantic model for consistent API error format
  - TradeRequest/TradeResponse/PositionDetail/PortfolioResponse/SnapshotPoint Pydantic models
  - execute_trade service with atomic DB transaction (buy/sell with validation)
  - get_portfolio service enriching positions with live PriceCache prices and P&L
  - record_snapshot service for portfolio value persistence
  - GET /api/portfolio endpoint returning positions with unrealized P&L
  - POST /api/portfolio/trade endpoint executing market orders
  - GET /api/portfolio/history endpoint returning portfolio snapshots
affects: [02-02-background-tasks-watchlist, 03-llm-chat, 04-frontend-foundation]

tech-stack:
  added: []
  patterns: [service-layer-separation, atomic-db-transaction, pydantic-field-validators, weighted-average-cost-upsert]

key-files:
  created:
    - backend/app/models/__init__.py
    - backend/app/models/common.py
    - backend/app/models/portfolio.py
    - backend/app/services/__init__.py
    - backend/app/services/portfolio.py
    - backend/app/routes/portfolio.py
    - backend/app/routes/portfolio_history.py
    - backend/tests/test_trade_service.py
    - backend/tests/test_portfolio.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Service layer pattern: routes stay thin, all business logic in services/portfolio.py for reuse by LLM chat in Phase 3"
  - "Epsilon comparison (abs < 1e-9) for zero-quantity position deletion to avoid float precision issues"
  - "record_snapshot called after trade (PORT-09) in the route handler, outside the trade transaction, so snapshot sees committed state"
  - "Cash amounts rounded to 2 decimal places in service layer to mitigate float drift (Pitfall 4)"

patterns-established:
  - "Service layer: routes import from app.services.* for business logic, keeping route handlers < 15 lines"
  - "Pydantic field_validator: strip+transform input (ticker uppercase, side lowercase) before validation"
  - "Atomic trade: pool.acquire() -> conn.transaction() wraps all position/cash/trade-log mutations"
  - "ErrorResponse: JSONResponse(status_code=400, content=ErrorResponse(...).model_dump()) for business validation errors"

requirements-completed: [PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-09, PORT-11]

duration: 4min
completed: 2026-03-02
---

# Phase 2 Plan 01: Portfolio APIs Summary

**Atomic trade execution service with weighted-average-cost position upsert, portfolio P&L enrichment from live PriceCache, and three REST endpoints for portfolio state, trade execution, and history**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T08:36:58Z
- **Completed:** 2026-03-02T08:41:37Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Trade execution with atomic DB transactions: buy (cash validation, position upsert with weighted avg cost), sell (share validation, position update/delete at zero qty), trade logging
- Portfolio query enriching DB positions with live PriceCache prices to compute unrealized P&L and pnl_percent per position
- Three API endpoints: GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
- Pydantic validators providing automatic 422 errors for invalid ticker (non-alpha or >5 chars), invalid side (not buy/sell), and non-positive quantity
- 25 new tests passing (14 service-level + 11 route-level), 155 total tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for portfolio service** - `70bac58` (test)
2. **Task 1 (GREEN): Portfolio service implementation** - `e6172ba` (feat)
3. **Task 2 (RED): Failing tests for route handlers** - `95d5003` (test)
4. **Task 2 (GREEN): Route handlers and main.py wiring** - `ee0ce02` (feat)

_TDD tasks each have two commits (test then implementation)_

## Files Created/Modified
- `backend/app/models/__init__.py` - Package marker for Pydantic models
- `backend/app/models/common.py` - ErrorResponse shared model for consistent API errors
- `backend/app/models/portfolio.py` - TradeRequest (with validators), TradeResponse, PositionDetail, PortfolioResponse, SnapshotPoint models
- `backend/app/services/__init__.py` - Package marker for service layer
- `backend/app/services/portfolio.py` - execute_trade, get_portfolio, record_snapshot business logic
- `backend/app/routes/portfolio.py` - GET /api/portfolio and POST /api/portfolio/trade handlers
- `backend/app/routes/portfolio_history.py` - GET /api/portfolio/history handler
- `backend/app/main.py` - Added portfolio_router and portfolio_history_router registration
- `backend/tests/test_trade_service.py` - 14 tests for service-level trade execution, portfolio query, snapshots
- `backend/tests/test_portfolio.py` - 11 tests for route-level HTTP status codes, response shapes, validation

## Decisions Made
- Service layer pattern adopted: routes stay thin (<15 lines), all business logic in services/portfolio.py. This enables Phase 3 LLM chat to reuse execute_trade directly.
- Epsilon comparison (abs < 1e-9) used for zero-quantity position deletion instead of exact float equality, for robustness against floating-point drift.
- record_snapshot called in the route handler after trade transaction commits (not inside the transaction), ensuring the snapshot reads the committed state (Pitfall 5 avoidance).
- All monetary calculations rounded to 2 decimal places at the service layer to prevent float drift accumulation (Pitfall 4 mitigation).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Portfolio service layer complete and tested, ready for Plan 02-02 (background tasks and watchlist CRUD)
- Services package structure ready for watchlist service
- Models package ready for watchlist models
- Background task (snapshot recorder) will reuse record_snapshot from services/portfolio.py
- LLM chat (Phase 3) can import execute_trade directly for auto-execution
- 155 tests passing, all green

## Self-Check: PASSED

All 10 files verified present. All 4 commit hashes found in git log.

---
*Phase: 02-portfolio-watchlist-apis*
*Completed: 2026-03-02*
