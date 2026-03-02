---
phase: 06-docker-e2e-tests
plan: 02
subsystem: testing
tags: [playwright, e2e, docker-compose, chromium, testing, sse, mock-llm]

# Dependency graph
requires:
  - phase: 06-docker-e2e-tests
    provides: Docker infrastructure (Dockerfiles, docker-compose.yml) from Plan 06-01
  - phase: 05-visualizations-chat-panel
    provides: Complete frontend with all UI components (watchlist, trade bar, chat panel)
  - phase: 03-llm-chat-integration
    provides: Mock LLM mode (LLM_MOCK=true) for deterministic chat responses
provides:
  - Playwright E2E test suite with 17 tests across 4 spec files
  - docker-compose.test.yml for running tests against containerized app
  - Test infrastructure (package.json, tsconfig, playwright.config.ts)
affects: []

# Tech tracking
tech-stack:
  added: ["@playwright/test@1.52.0"]
  patterns: [e2e-test-against-docker-stack, mock-llm-for-deterministic-tests, sse-timeout-patterns]

key-files:
  created:
    - test/package.json
    - test/package-lock.json
    - test/tsconfig.json
    - test/playwright.config.ts
    - test/docker-compose.test.yml
    - test/tests/smoke.spec.ts
    - test/tests/watchlist.spec.ts
    - test/tests/trading.spec.ts
    - test/tests/chat.spec.ts
  modified: []

key-decisions:
  - "Self-contained docker-compose.test.yml rather than include directive (Compose V2 include cannot override imported services)"
  - "Playwright v1.52.0 pinned to match Docker image tag mcr.microsoft.com/playwright:v1.52.0-noble"
  - "Single chromium project with workers:1 since tests share database state"
  - "15s timeouts for SSE-dependent assertions (container startup + SSE connection time)"
  - "Selectors matched to actual DOM: placeholder='AAPL', placeholder='10', placeholder='Ask FinAlly...'"

patterns-established:
  - "E2E tests use generous timeouts (15s) for SSE data arrival in containerized environments"
  - "Chat tests verify exact mock response text from _mock_response() in chat.py"
  - "Trading tests assert on toast notifications for buy/sell confirmation"

requirements-completed: [OPS-06]

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 06 Plan 02: Playwright E2E Test Suite Summary

**17 Playwright E2E tests across smoke, watchlist, trading, and chat specs with docker-compose.test.yml for containerized execution**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T23:02:29Z
- **Completed:** 2026-03-02T23:05:23Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Complete Playwright test infrastructure with package.json, TypeScript config, and Playwright config targeting chromium with BASE_URL env var
- Self-contained docker-compose.test.yml defining backend (LLM_MOCK=true), frontend, and Playwright container
- 17 E2E tests covering: app load, SSE streaming, cash balance, watchlist (10 tickers, live prices), trading (buy, sell, error handling), and AI chat (panel toggle, send/receive messages, mock response verification)
- All selectors verified against actual frontend component source (TradeBar, ChatPanel, Header, WatchlistPanel, Dashboard)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test infrastructure and docker-compose.test.yml** - `6aa22b8` (feat)
2. **Task 2: Create E2E test spec files for smoke, watchlist, trading, and chat** - `a4f57f5` (feat)

## Files Created/Modified
- `test/package.json` - Minimal package with @playwright/test@1.52.0 and test scripts
- `test/package-lock.json` - Generated lockfile for reproducible installs
- `test/tsconfig.json` - ES2022 strict TypeScript config for test files
- `test/playwright.config.ts` - Chromium-only project, BASE_URL from env, 30s timeout, html+list reporters
- `test/docker-compose.test.yml` - Self-contained stack: backend (LLM_MOCK=true), frontend, Playwright v1.52.0 container
- `test/tests/smoke.spec.ts` - 5 tests: app loads, SSE streams, cash balance, portfolio value, connection status
- `test/tests/watchlist.spec.ts` - 3 tests: 10 default tickers, live dollar prices, watchlist heading
- `test/tests/trading.spec.ts` - 4 tests: buy shares, sell shares, insufficient shares error, cash decreases
- `test/tests/chat.spec.ts` - 5 tests: panel visible, collapse/reopen, send message with mock response, user message history, empty state

## Decisions Made
- **Self-contained compose file:** Docker Compose V2's `include` directive does not support overriding services from included files. Instead of `include + override`, the test compose file defines all three services directly (backend, frontend, playwright) with the backend's `LLM_MOCK=true` environment override.
- **Exact version pinning:** @playwright/test@1.52.0 in package.json matches mcr.microsoft.com/playwright:v1.52.0-noble Docker image to avoid version mismatch issues.
- **Serial execution:** `workers: 1` and `fullyParallel: false` because tests share a database (trades in one test affect portfolio state in another).
- **DOM-accurate selectors:** All selectors verified against actual component source rather than using generic patterns. TradeBar uses `placeholder="AAPL"` and `placeholder="10"` (not "ticker"/"quantity"). ChatPanel uses `placeholder="Ask FinAlly..."`.
- **Toast-based trade assertions:** Trading tests verify success/error via Sonner toast notifications (`/Bought .* AAPL/`, `/Sold .* AAPL/`, `/insufficient|not enough|no position/i`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Docker Compose include directive incompatibility**
- **Found during:** Task 1 (docker-compose.test.yml creation)
- **Issue:** `include: path: ../docker-compose.yml` with `services: backend: environment: LLM_MOCK=true` fails validation because Compose V2 `include` does not allow overriding imported services in the same file
- **Fix:** Replaced `include` pattern with self-contained service definitions that replicate the main compose structure with the LLM_MOCK override
- **Files modified:** test/docker-compose.test.yml
- **Verification:** `docker compose -f docker-compose.test.yml config` validates successfully
- **Committed in:** a4f57f5 (Task 2 commit, since compose file was updated)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary fix for Docker Compose compatibility. The self-contained approach is actually more explicit and maintainable than the include pattern.

## Issues Encountered
None beyond the compose include issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- E2E test suite is ready to run against the containerized stack
- Full validation command: `cd test && docker compose -f docker-compose.test.yml run --rm playwright`
- This completes Phase 6 (Docker & E2E Tests) -- the final phase of the FinAlly project
- All 6 phases are now complete: DB Foundation, APIs, LLM Chat, Frontend Foundation, Visualizations, Docker & E2E

## Self-Check: PASSED

All 9 files verified present. Both task commits (6aa22b8, a4f57f5) verified in git log.

---
*Phase: 06-docker-e2e-tests*
*Completed: 2026-03-02*
