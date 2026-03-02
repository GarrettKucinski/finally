---
phase: 01-database-foundation
plan: 01
subsystem: database
tags: [asyncpg, pydantic-settings, postgres, neon, fastapi, sql]

requires:
  - phase: none (first plan)
    provides: n/a
provides:
  - Pydantic Settings class for all env vars (config.py)
  - asyncpg pool lifecycle with Neon-compatible settings (db.py)
  - SQL schema for all 7 database tables (tables.sql)
  - Idempotent seed data for default user, profile, watchlist (seed.sql)
  - FastAPI app with lifespan wiring DB + market data (main.py)
affects: [01-02-health-endpoint, 02-portfolio-watchlist-apis, 03-llm-chat]

tech-stack:
  added: [pydantic-settings, asyncpg]
  patterns: [pydantic-settings-validation, asyncpg-pool-lifecycle, sql-file-loading, lifespan-context-manager, app-state-injection]

key-files:
  created:
    - backend/app/config.py
    - backend/app/db.py
    - backend/app/main.py
    - backend/app/schema/__init__.py
    - backend/app/schema/tables.sql
    - backend/app/schema/seed.sql
    - backend/tests/test_config.py
    - backend/tests/test_db.py
  modified:
    - backend/tests/conftest.py

key-decisions:
  - "Settings not instantiated at module level -- use get_settings() to avoid breaking tests that control env vars"
  - "SQL files loaded at module import time via pathlib for efficiency"
  - "Pool uses statement_cache_size=0 for Neon serverless Postgres compatibility"
  - "Seed uses fixed UUID 00000000-0000-0000-0000-000000000001 for default user"

patterns-established:
  - "Pydantic Settings: env vars validated on instantiation, fail-fast on missing required"
  - "DB lifecycle: init_db/close_db functions called from FastAPI lifespan"
  - "Schema execution: SQL files read from app/schema/ directory"
  - "Conditional seeding: check user count before inserting seed data"
  - "App state: shared resources (pool, cache, source) stored on app.state"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03]

duration: 4min
completed: 2026-03-02
---

# Phase 1 Plan 01: Database Foundation Summary

**Pydantic Settings validation, asyncpg pool with Neon-compatible config, 7-table SQL schema, idempotent seed data, and FastAPI lifespan wiring DB + market data subsystem**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T07:54:52Z
- **Completed:** 2026-03-02T07:58:24Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Settings class validates DATABASE_URL on startup, fails fast with clear error if missing
- asyncpg pool created with statement_cache_size=0 for Neon serverless compatibility
- All 7 tables defined in FK-safe order with correct types, PKs, FKs, and unique constraints
- Default user ($10k cash, 10 watchlist tickers) seeded idempotently via ON CONFLICT DO NOTHING
- FastAPI app lifespan wires Settings -> DB -> watchlist query -> PriceCache -> market data -> SSE router
- 14 new unit tests passing, 127 total tests passing (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for Settings and DB** - `0e6a512` (test)
2. **Task 1 (GREEN): Settings, DB pool, schema, seed implementation** - `ddbae7c` (feat)
3. **Task 2: FastAPI main.py with lifespan** - `62a62b7` (feat)

## Files Created/Modified
- `backend/app/config.py` - Pydantic Settings class for all env vars with get_settings() caching
- `backend/app/db.py` - asyncpg pool init/close, schema execution, conditional seeding
- `backend/app/main.py` - FastAPI app with lifespan wiring DB and market data
- `backend/app/schema/__init__.py` - Package marker
- `backend/app/schema/tables.sql` - DDL for all 7 tables (users, users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages)
- `backend/app/schema/seed.sql` - Default user, profile ($10k), 10 watchlist tickers
- `backend/tests/test_config.py` - 3 tests for Settings validation and defaults
- `backend/tests/test_db.py` - 11 tests for pool params, schema content, seed logic, close
- `backend/tests/conftest.py` - Updated with mock_pool, mock_conn, env fixtures

## Decisions Made
- Settings not instantiated at module level to avoid breaking tests that need to control env vars before creation
- SQL files loaded at module import time via pathlib for efficiency (read once, used on every startup)
- Pool uses statement_cache_size=0 because Neon's serverless connection pooler does not support prepared statements
- Fixed UUID `00000000-0000-0000-0000-000000000001` for default user to enable deterministic references

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test for Settings defaults picking up .env file**
- **Found during:** Task 1 (GREEN phase - running tests)
- **Issue:** test_settings_defaults was asserting openrouter_api_key == "" but the .env file in the project root had OPENROUTER_API_KEY set, which Pydantic Settings loaded automatically
- **Fix:** Added `_env_file=None` to Settings() constructor in the test and monkeypatched relevant env vars
- **Files modified:** backend/tests/test_config.py
- **Verification:** All 14 tests pass
- **Committed in:** ddbae7c (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test fix necessary for correctness. No scope creep.

## Issues Encountered
- AsyncMock for pool.acquire() context manager needed custom asynccontextmanager wrapper since asyncpg's acquire() returns a sync context manager that yields an awaitable, not a coroutine -- resolved by using contextlib.asynccontextmanager in test helper

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Database foundation complete: pool, schema, seed, and app entry point all functional
- Ready for Plan 01-02: health endpoint and integration testing
- All 127 tests passing (113 existing market data + 14 new config/DB tests)

---
*Phase: 01-database-foundation*
*Completed: 2026-03-02*
