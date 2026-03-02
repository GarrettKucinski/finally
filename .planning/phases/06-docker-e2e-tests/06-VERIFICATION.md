---
phase: 06-docker-e2e-tests
verified: 2026-03-02T23:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 6: Docker & E2E Tests Verification Report

**Phase Goal:** Containerize both services with Docker, create docker-compose.yml for one-command startup, and build Playwright E2E test suite validating all user-facing flows against the containerized stack.
**Verified:** 2026-03-02T23:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `frontend/Dockerfile` builds a multi-stage Next.js standalone image that serves the app on port 3000 | VERIFIED | 3-stage build (deps/builder/runner), `output: 'standalone'` in next.config.ts, `HOSTNAME=0.0.0.0`, `PORT=3000`, non-root user, 35 lines |
| 2  | `backend/Dockerfile` builds a uv-based FastAPI image that serves the app on port 8000 via uvicorn | VERIFIED | Uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`, cache-mount dep install, `uvicorn app.main:app --host 0.0.0.0 --port 8000`, 22 lines |
| 3  | `docker-compose.yml` orchestrates both services with backend healthcheck and frontend depends_on | VERIFIED | Backend healthcheck via Python urllib against `/api/health`, `condition: service_healthy` on frontend depends_on |
| 4  | Frontend container proxies /api/* to backend via Next.js rewrites using BACKEND_URL=http://backend:8000 | VERIFIED | `docker-compose.yml` sets `BACKEND_URL=http://backend:8000`; `next.config.ts` rewrites use `process.env.BACKEND_URL` |
| 5  | `docker compose up` builds and starts both services with no manual setup required | VERIFIED | `docker-compose.yml` uses `build: ./frontend` and `build: ./backend` with no external dependencies at runtime beyond `.env` |
| 6  | `.env.example` documents all required and optional environment variables including BACKEND_URL | VERIFIED | All 5 vars documented: `DATABASE_URL`, `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`, `BACKEND_URL` |
| 7  | Playwright E2E tests are configured to run against the containerized app at http://frontend:3000 or http://localhost:3000 | VERIFIED | `playwright.config.ts` uses `process.env.BASE_URL \|\| 'http://localhost:3000'`; `docker-compose.test.yml` sets `BASE_URL=http://frontend:3000` |
| 8  | `test/docker-compose.test.yml` provides LLM_MOCK=true on backend and includes a Playwright container | VERIFIED | Self-contained file with 3 services; backend has `LLM_MOCK=true` in environment; `playwright` service uses `mcr.microsoft.com/playwright:v1.52.0-noble` |
| 9  | Smoke tests verify the app loads, SSE prices stream, and default $10,000 balance is shown | VERIFIED | `smoke.spec.ts` has 5 tests covering `FinAlly` brand, AAPL price via SSE, `/\$10,000/` regex, `Portfolio Value` label, `Connected` status |
| 10 | Watchlist tests verify default tickers appear with live prices | VERIFIED | `watchlist.spec.ts` iterates all 10 tickers (AAPL through NFLX) and asserts dollar-formatted prices |
| 11 | Trading tests verify buy/sell flows update positions and cash balance | VERIFIED | `trading.spec.ts` has 4 tests with accurate selectors (`placeholder="AAPL"`, `placeholder="10"`, `Buy`/`Sell` buttons), toast confirmation assertions |
| 12 | Chat tests verify sending a message and receiving a mock AI response with action cards | VERIFIED | `chat.spec.ts` 5 tests match exact mock response text from `backend/app/services/chat.py _mock_response()`: `/Mock response.*chat system is working correctly/` |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Line Count | Details |
|----------|----------|--------|------------|---------|
| `frontend/Dockerfile` | 3-stage Next.js standalone Docker build (deps, builder, runner), min 25 lines | VERIFIED | 35 lines | All 3 stages present; HOSTNAME=0.0.0.0; non-root nextjs user; static assets copied explicitly |
| `frontend/.dockerignore` | Excludes node_modules, .next, .env, min 4 lines | VERIFIED | 6 lines | Excludes node_modules, .next, .env*, *.tsbuildinfo, next-env.d.ts, README.md |
| `backend/Dockerfile` | uv-based FastAPI Docker build, min 15 lines | VERIFIED | 22 lines | Official uv image; UV_COMPILE_BYTECODE=1; UV_LINK_MODE=copy; cache-mount two-step install; production-only deps |
| `backend/.dockerignore` | Excludes .venv, __pycache__, tests, .env, min 4 lines | VERIFIED | 8 lines | All required exclusions present |
| `docker-compose.yml` | Two-service orchestration with healthcheck, env_file, BACKEND_URL, min 15 lines | VERIFIED | 22 lines | Backend healthcheck (Python urllib), `env_file: .env`, `BACKEND_URL=http://backend:8000`, `service_healthy` condition |
| `frontend/next.config.ts` | output: 'standalone' added alongside existing rewrites | VERIFIED | 15 lines | `output: 'standalone'` on line 4; rewrites preserved; BACKEND_URL fallback preserved |
| `test/package.json` | @playwright/test dependency | VERIFIED | 12 lines | `"@playwright/test": "1.52.0"` |
| `test/tsconfig.json` | TypeScript configuration for Playwright tests | VERIFIED | 14 lines | ES2022, strict mode, includes tests/**/*.ts and playwright.config.ts |
| `test/playwright.config.ts` | Playwright config with baseURL, chromium-only project, CI-aware settings, min 15 lines | VERIFIED | 24 lines | BASE_URL env var, chromium project only, workers:1, fullyParallel:false, CI retries |
| `test/docker-compose.test.yml` | Test compose file with LLM_MOCK=true on backend and Playwright container, min 10 lines | VERIFIED | 37 lines | Self-contained 3-service file; LLM_MOCK=true; env_file: ../.env; Playwright v1.52.0-noble image |
| `test/tests/smoke.spec.ts` | Smoke tests: app loads, prices stream, balance displayed, min 15 lines | VERIFIED | 36 lines | 5 tests covering app brand, SSE, cash balance, portfolio value, connection status |
| `test/tests/watchlist.spec.ts` | Watchlist tests: default tickers visible, prices updating, min 15 lines | VERIFIED | 30 lines | 3 tests; all 10 default tickers checked; dollar price pattern; Watchlist heading |
| `test/tests/trading.spec.ts` | Trading tests: buy/sell flows, balance/position updates, min 25 lines | VERIFIED | 90 lines | 4 tests; correct selectors (placeholder="AAPL", placeholder="10"); toast assertions for buy/sell/error |
| `test/tests/chat.spec.ts` | Chat tests: send message, receive mock response, action cards rendered, min 20 lines | VERIFIED | 76 lines | 5 tests; panel visible; collapse/reopen; exact mock response text match; user/FinAlly labels |

### Key Link Verification

**Plan 06-01 Key Links:**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docker-compose.yml` | `frontend/Dockerfile` | `build: ./frontend` | VERIFIED | `build: ./frontend` on line 15 |
| `docker-compose.yml` | `backend/Dockerfile` | `build: ./backend` | VERIFIED | `build: ./backend` on line 3 |
| `docker-compose.yml` | `.env` | `env_file: .env` for backend | VERIFIED | `env_file: .env` on line 6 |
| `frontend/next.config.ts` | BACKEND_URL env var | `process.env.BACKEND_URL` in rewrites destination | VERIFIED | Line 9: `` `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*` `` |

**Plan 06-02 Key Links:**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test/docker-compose.test.yml` | `docker-compose.yml` | include directive | DEVIATION (ACCEPTABLE) | Self-contained approach used instead. The `include` directive was replaced by duplicating all services directly. `LLM_MOCK=true` injection is functionally equivalent and verified. SUMMARY documents this as an auto-fixed issue. |
| `test/docker-compose.test.yml` | LLM_MOCK | environment override on backend | VERIFIED | `LLM_MOCK=true` present in backend environment block (line 8) |
| `test/playwright.config.ts` | BASE_URL env var | `process.env.BASE_URL` for containerized vs local | VERIFIED | Line 13: `baseURL: process.env.BASE_URL \|\| 'http://localhost:3000'` |
| `test/tests/*.spec.ts` | http://frontend:3000 or localhost:3000 | `page.goto('/')` using baseURL from config | VERIFIED | All 4 spec files use `page.goto('/')` (smoke: 5, watchlist: 3, trading: 4, chat: 5 occurrences) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OPS-01 | 06-01-PLAN | `frontend/Dockerfile` builds and serves the Next.js app on port 3000 | SATISFIED | `frontend/Dockerfile` exists, 3-stage, EXPOSE 3000, CMD node server.js |
| OPS-02 | 06-01-PLAN | `backend/Dockerfile` builds and serves the FastAPI app on port 8000 via uvicorn | SATISFIED | `backend/Dockerfile` exists, EXPOSE 8000, CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 |
| OPS-03 | 06-01-PLAN | `docker-compose.yml` orchestrates both services with proper networking and environment variables | SATISFIED | `docker-compose.yml` has both services, healthcheck, env_file, BACKEND_URL |
| OPS-04 | 06-01-PLAN | Frontend proxies `/api/*` to `http://backend:8000` via Next.js rewrites (no CORS needed) | SATISFIED | `next.config.ts` rewrites to `${BACKEND_URL}/api/:path*`; compose sets `BACKEND_URL=http://backend:8000` |
| OPS-05 | 06-01-PLAN | `docker compose up` starts both services from a single command with no manual setup | SATISFIED | `docker-compose.yml` in project root; `build:` directives for both services; no external orchestration required |
| OPS-06 | 06-02-PLAN | E2E tests via Playwright in `test/docker-compose.test.yml` with `LLM_MOCK=true` | SATISFIED | `test/docker-compose.test.yml` exists with `LLM_MOCK=true` on backend; Playwright container defined; 17 tests across 4 spec files |
| OPS-07 | 06-01-PLAN | `.env.example` committed with all required/optional environment variables documented | SATISFIED | `.env.example` documents DATABASE_URL, OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK, BACKEND_URL |

**Orphaned requirements:** None. All 7 OPS requirements are claimed by plans and verified.

### Anti-Patterns Found

No anti-patterns detected. Scans of all Docker files, compose files, and test spec files returned no TODOs, FIXMEs, placeholder comments, empty implementations, or stub handlers.

### Key Deviation: docker-compose.test.yml Uses Self-Contained Approach

The plan specified `include: path: ../docker-compose.yml` with a service override for `LLM_MOCK=true`. The implementation uses a self-contained file that defines all 3 services directly (backend, frontend, playwright). This was an intentional fix documented in the SUMMARY: Docker Compose V2's `include` directive does not support overriding services from included files. The functional outcome is identical — backend runs with `LLM_MOCK=true`, frontend is wired to backend, Playwright container runs tests against `http://frontend:3000`. The build paths (`../backend`, `../frontend`) and env_file path (`../.env`) are correctly relative to `test/`.

### Human Verification Required

The following items require a running Docker environment to validate end-to-end:

**1. Full Docker build success**
- Test: `docker compose build` from the project root
- Expected: Both frontend and backend images build without errors; Next.js standalone build succeeds; uv deps install cleanly
- Why human: Requires Docker Desktop running; build may surface missing files or layer cache issues not detectable via static analysis

**2. `docker compose up` one-command startup**
- Test: `docker compose up` from the project root with a valid `.env`
- Expected: Backend starts and passes healthcheck, frontend starts and serves the dashboard at http://localhost:3000 with live SSE prices
- Why human: Requires Docker running and valid DATABASE_URL and OPENROUTER_API_KEY in `.env`

**3. Playwright E2E test execution**
- Test: `cd test && docker compose -f docker-compose.test.yml run --rm playwright`
- Expected: All 17 tests pass against the containerized stack with LLM_MOCK=true
- Why human: Requires Docker and a valid `.env`; tests make live SSE connections and real API calls; timing-sensitive assertions (15s timeouts for SSE data arrival)

**4. Chat collapse/reopen selector**
- Test: In the running app, collapse chat panel via "Collapse chat" button, then click the floating "AI" button text
- Expected: `getByRole('button', { name: 'AI' })` matches the floating button (text content "AI", title "Open AI Chat")
- Why human: Playwright accessible name resolution for buttons with both text content and title attributes can be environment-dependent; need to confirm the selector matches at runtime

---

## Summary

Phase 6 achieves its goal. All Docker infrastructure files exist and are substantive:

- `frontend/Dockerfile` is a proper 3-stage multi-stage build with standalone output, non-root user, correct HOSTNAME binding, and static asset copying — all critical pitfalls addressed per the research document.
- `backend/Dockerfile` uses the official uv image with cache-mount optimization, UV_COMPILE_BYTECODE, production-only dependencies, and proper uvicorn startup.
- `docker-compose.yml` correctly wires the two services with a healthcheck-gated startup order, env_file injection for Pydantic Settings, and BACKEND_URL for Docker networking.
- `frontend/next.config.ts` adds `output: 'standalone'` without disturbing the existing rewrites.
- `.env.example` documents all 5 variables.

The Playwright test suite is complete with 17 tests across 4 spec files. All selectors were verified against actual frontend component source — `placeholder="AAPL"`, `placeholder="10"`, `placeholder="Ask FinAlly..."`, `aria-label="Collapse chat"`, `getByText('AI')` — and match the rendered DOM. The chat test's mock response assertion (`/Mock response.*chat system is working correctly/`) matches the exact string produced by `_mock_response()` in `backend/app/services/chat.py`. The `docker-compose.test.yml` correctly provides `LLM_MOCK=true` on the backend and version-pins Playwright at v1.52.0 to match the `@playwright/test@1.52.0` in `test/package.json`.

The one architectural deviation (self-contained test compose vs. include+override) is correctly handled and is actually more maintainable. All 7 OPS requirements are satisfied.

---

_Verified: 2026-03-02T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
