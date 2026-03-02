---
phase: 02-portfolio-watchlist-apis
plan: 02
subsystem: api
tags: [fastapi, asyncpg, pydantic, watchlist, background-tasks, market-data-sync]

requires:
  - phase: 02-portfolio-watchlist-apis plan 01
    provides: Service layer pattern, ErrorResponse model, record_snapshot function, app.state wiring for db_pool/price_cache/market_source
  - phase: 01-database-foundation plan 01
    provides: asyncpg pool, watchlist/portfolio_snapshots tables, seed data
provides:
  - AddTickerRequest and WatchlistItem Pydantic models for watchlist API
  - get_watchlist service enriching DB rows with PriceCache live prices
  - add_ticker service with DB insert + market source registration (WATCH-04)
  - remove_ticker service with DB delete + market source unregistration (WATCH-05)
  - GET/POST/DELETE /api/watchlist route handlers
  - snapshot_recorder_loop background task recording portfolio value every 30s (PORT-08)
  - snapshot_cleanup_loop background task deleting snapshots older than 24h (PORT-10)
  - Lifespan wiring for background tasks with proper shutdown cancellation
affects: [03-llm-chat, 04-frontend-foundation]

tech-stack:
  added: []
  patterns: [watchlist-market-source-sync, asyncio-background-task-lifecycle, on-conflict-do-nothing-returning]

key-files:
  created:
    - backend/app/models/watchlist.py
    - backend/app/services/watchlist.py
    - backend/app/routes/watchlist.py
    - backend/app/tasks/__init__.py
    - backend/app/tasks/snapshots.py
    - backend/tests/test_watchlist.py
    - backend/tests/test_snapshots.py
  modified:
    - backend/app/main.py

key-decisions:
  - "ON CONFLICT DO NOTHING + RETURNING id pattern for duplicate detection: returns None when row already exists, avoiding UniqueViolationError"
  - "DELETE result string parsing (DELETE 0 vs DELETE 1) for 404 handling per asyncpg behavior"
  - "Background tasks cancelled before DB pool close to prevent event loop errors on shutdown (Pitfall 3)"
  - "Watchlist router registered in main.py during Task 1 (moved from Task 2) as blocking dependency for tests"

patterns-established:
  - "Market source sync: add_ticker/remove_ticker always called after DB mutation succeeds, never before"
  - "Background task pattern: while True + try/except + asyncio.sleep, launched via create_task in lifespan, cancelled on shutdown"
  - "ON CONFLICT DO NOTHING + RETURNING id: returns None for duplicates, avoids catching UniqueViolationError"

requirements-completed: [WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05, PORT-08, PORT-10]

duration: 3min
completed: 2026-03-02
---

# Phase 2 Plan 02: Watchlist & Background Tasks Summary

**Watchlist CRUD endpoints with market data source sync (add/remove tickers register with live price stream) and background tasks for periodic portfolio snapshot recording every 30s with 24h cleanup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T08:45:24Z
- **Completed:** 2026-03-02T08:49:03Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Watchlist CRUD: GET returns tickers enriched with live PriceCache data (price, change, direction), POST validates ticker format (1-5 alpha) and registers with market source, DELETE unregisters from market source
- Background snapshot recorder loop running every 30 seconds, reusing record_snapshot from portfolio service
- Background cleanup loop deleting snapshots older than 24 hours every 5 minutes
- Both background tasks handle errors gracefully (log + continue) and are properly cancelled on shutdown before DB pool close
- 16 new tests (11 watchlist + 5 snapshot), 171 total tests passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Watchlist model, service, and routes with market data sync** - `4f3ae8c` (feat)
2. **Task 2: Background snapshot tasks and main.py lifespan wiring** - `b79fee8` (feat)

## Files Created/Modified
- `backend/app/models/watchlist.py` - AddTickerRequest (with validator) and WatchlistItem Pydantic models
- `backend/app/services/watchlist.py` - get_watchlist, add_ticker, remove_ticker with market source sync
- `backend/app/routes/watchlist.py` - GET/POST/DELETE /api/watchlist route handlers
- `backend/app/tasks/__init__.py` - Background tasks package marker
- `backend/app/tasks/snapshots.py` - snapshot_recorder_loop (30s) and snapshot_cleanup_loop (5min)
- `backend/app/main.py` - Added watchlist router, background task imports, create_task in lifespan, shutdown cancellation
- `backend/tests/test_watchlist.py` - 11 tests for watchlist routes and market source sync
- `backend/tests/test_snapshots.py` - 5 tests for background task loops, error handling, intervals

## Decisions Made
- Used ON CONFLICT DO NOTHING + RETURNING id pattern instead of catching UniqueViolationError for duplicate detection. Cleaner: returns None when row already exists.
- DELETE result string parsing ("DELETE 0" check) for 404 handling, following asyncpg's documented behavior (Pitfall 2 from research).
- Background tasks cancelled before DB pool close in shutdown sequence, preventing "event loop is closed" errors (Pitfall 3 from research).
- Watchlist router registration moved from Task 2 to Task 1 since tests required routes to be accessible via httpx.ASGITransport.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Watchlist router registration moved to Task 1**
- **Found during:** Task 1 (test writing)
- **Issue:** Plan specified registering watchlist router in main.py during Task 2, but Task 1 tests needed routes accessible
- **Fix:** Added `app.include_router(watchlist_router)` in Task 1 alongside route creation
- **Files modified:** backend/app/main.py
- **Verification:** All 11 watchlist tests pass
- **Committed in:** 4f3ae8c (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial reordering of a single line registration. No scope creep.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 2 complete: all portfolio and watchlist APIs implemented and tested
- Services layer (execute_trade, get_portfolio, get_watchlist, add_ticker, remove_ticker) ready for Phase 3 LLM chat auto-execution
- Background tasks running for P&L chart data (snapshot recorder) and data hygiene (cleanup)
- 171 tests passing, all green
- Ready for Phase 3: LLM Chat Integration

## Self-Check: PASSED

All 8 files verified present. Both commit hashes found in git log.

---
*Phase: 02-portfolio-watchlist-apis*
*Completed: 2026-03-02*
