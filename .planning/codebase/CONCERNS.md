# Codebase Concerns

**Analysis Date:** 2026-03-01

## Project Status

The market data subsystem is **complete and production-ready** with 113 passing tests and 96% line coverage. However, the overall FinAlly platform remains partially implemented with significant structural gaps.

---

## Architectural Gaps

### Missing Core Backend Services

**Critical issue:** The backend only implements market data streaming. All other required services are absent.

**Files:**
- `/Users/garrettkucinski/dev/agentic-coding/finally/backend/app/` contains only `market/` subdirectory

**What's missing:**
- Portfolio management API endpoints (trades, positions, cash balance)
- Watchlist CRUD endpoints
- Database layer (schema, models, ORM migrations)
- LLM integration and chat API
- Portfolio snapshot recording (for P&L charts)
- User management and authentication
- Health check endpoints

**Impact:**
- Cannot run `docker compose up` — missing services will fail immediately
- No way to execute trades, manage positions, or store data persistently
- No chat functionality or LLM integration
- Frontend cannot function even if complete

**Fix approach:**
- Implement remaining FastAPI routes for portfolio, watchlist, and chat operations
- Set up database schema initialization in FastAPI lifespan event
- Implement trade execution logic with validation (cash balance, position checks)
- Integrate LLM calls with structured output parsing
- Create background task for recording portfolio snapshots every 30 seconds

---

### Frontend Directory is Empty

**Critical issue:** The frontend is a placeholder directory with no implementation.

**Files:**
- `/Users/garrettkucinski/dev/agentic-coding/finally/frontend/` — empty (2 files: `.` and `..`)

**What's missing:**
- Next.js project initialization
- React components for watchlist, charts, portfolio heatmap, P&L chart
- Trade execution UI (ticker/quantity inputs, buy/sell buttons)
- AI chat panel with message history
- SSE client setup for price streaming
- Tailwind CSS configuration and dark theme
- TypeScript type definitions
- Charting library integration (Lightweight Charts or Recharts)
- Price flash animation CSS

**Impact:**
- No user interface exists
- Cannot test SSE streaming or portfolio display
- Docker build will fail (missing `package.json`, build output)

**Fix approach:**
- Initialize Next.js project with TypeScript
- Create component structure (Watchlist, ChartArea, PortfolioHeatmap, PortfolioTable, ChatPanel, Header)
- Set up EventSource listener for `/api/stream/prices`
- Implement trading bar and chat UI
- Configure Tailwind CSS with dark theme
- Add charting library and real-time price update logic

---

### Deployment Infrastructure Missing

**Critical issue:** No Docker Compose, Dockerfiles, or deployment configuration exists.

**Files:** None found
- `docker-compose.yml` — missing
- `frontend/Dockerfile` — missing
- `backend/Dockerfile` — missing
- `deploy/` directory — missing

**Impact:**
- Cannot run `docker compose up` as documented in PLAN.md
- Production deployment is impossible without containerization
- Local development requires manual setup of both services

**Fix approach:**
- Create `docker-compose.yml` with frontend and backend services
- Write `frontend/Dockerfile` (Node 20 slim, `npm install && npm run build`, expose port 3000)
- Write `backend/Dockerfile` (Python 3.12 slim, install uv, `uv sync`, expose port 8000)
- Set environment variables in compose file (BACKEND_URL, DATABASE_URL, etc.)

---

### Testing Infrastructure Incomplete

**Status:** Backend market data tests are excellent (113 tests, 96% coverage). Other areas lack test infrastructure.

**Files:**
- `/Users/garrettkucinski/dev/agentic-coding/finally/backend/tests/market/` — 7 test modules, comprehensive
- `/Users/garrettkucinski/dev/agentic-coding/finally/test/` — E2E tests and test docker-compose — **missing**

**Gaps:**
- No E2E Playwright tests for full user flows (watchlist, trading, chat)
- No test docker-compose configuration
- No portfolio/trade endpoint unit tests (not written yet)
- No LLM integration tests
- No frontend component tests

**Impact:**
- Cannot verify end-to-end workflows
- Trading logic has no test coverage (critical for correctness)
- Chat/LLM integration untested
- UI behavior unverified

**Fix approach:**
- Create `test/docker-compose.test.yml` with all three services plus Playwright
- Write E2E tests for: fresh start, add/remove ticker, buy/sell trades, portfolio display, chat interaction
- Add portfolio and trade endpoint unit tests in `backend/tests/`
- Set up frontend Jest/Vitest configuration for component testing
- Configure CI/CD to run tests on PR

---

## Known Limitations

### Market Data: Delayed Updates with Massive API

**Issue:** The Massive (Polygon.io) REST API client has a 15-second polling interval for free-tier compatibility.

**Files:** `backend/app/market/massive_client.py` (line 41, default `poll_interval=15.0`)

**Problem:**
- Prices stale for up to 15 seconds
- Real trading workstations update continuously (milliseconds)
- Lag may confuse users about actual execution prices

**Current mitigation:**
- GBM simulator runs at 500ms intervals (acceptable for demo)
- Default is to use simulator (MASSIVE_API_KEY unset)
- Version-based change detection prevents unnecessary SSE transmission

**Recommendation:** Document in UI that free-tier Massive shows "delayed prices" or switch to paid tier with faster polling (2–15 seconds).

---

### GBM Simulator: Correlation Matrix Assumptions

**Issue:** Correlation structure is hardcoded; doesn't reflect real market dynamics.

**Files:**
- `backend/app/market/seed_prices.py` (lines 11–45 define CORRELATION_GROUPS and SECTOR_INTRA_CORR)
- `backend/app/market/simulator.py` (line 176–188, _pairwise_correlation logic)

**Details:**
- Tech stocks (AAPL, MSFT, GOOGL, etc.) have 0.6 intra-sector correlation
- Finance stocks have 0.5 correlation
- TSLA is hardcoded to 0.3 with everything (intentionally "independent")
- Cross-sector correlation is 0.3

**Risk:**
- Correlations may become unrealistic as the watchlist grows with custom tickers
- Unknown tickers default to 0.3 with everything (assumed "consumer goods")
- No way to override correlation structure without code changes

**Recommendation:**
- Consider allowing correlation configuration via environment variables for custom scenarios
- Document assumptions in code comments
- For production, source real correlation matrices from historical data

---

### Cache Read Without Lock: Version Property

**Minor issue:** The `version` property in PriceCache wraps the read in a lock, which is correct, but it's inconsistent with how version is read in the SSE generator.

**Files:**
- `backend/app/market/cache.py` (lines 80–88, version property correctly uses lock)
- `backend/app/market/stream.py` (line 86, reads version in tight loop)

**Current status:** This is actually **correctly protected** in both locations. The concern from round 2 code review has been resolved.

**No action needed.**

---

## Performance Considerations

### SSE Polling Interval: 500ms CPU Cost

**Issue:** The SSE generator checks `cache.version` every 500ms in a tight loop.

**Files:** `backend/app/market/stream.py` (lines 62–102, _generate_events)

**Problem:**
- Each SSE client creates an async task that wakes every 500ms
- With 100+ concurrent clients, this becomes 200+ wake-ups per second
- Each wake involves lock acquisition on the cache

**Current mitigation:**
- Version-based change detection avoids serialization when nothing changed
- Lock is brief (just reading an integer)
- asyncio.sleep() is efficient

**Scaling threshold:** Expected to remain acceptable up to 1,000 concurrent users. Beyond that, consider:
- Batch SSE events (send updates every 1 second instead of 500ms)
- Use Redis pub/sub for multi-server deployments
- Switch to WebSocket with server-side subscriptions

**No immediate action needed** for single-user (MVP) phase.

---

## Configuration & Secrets

### Environment Variables: Good practices, but missing .env.example validation

**Issue:** While `.env.example` exists and documents all variables, there's no runtime schema validation for optional fields.

**Files:**
- `/Users/garrettkucinski/dev/agentic-coding/finally/.env.example` — good documentation
- `backend/pyproject.toml` — lists dependencies but no Pydantic settings class

**Missing:**
- No `Settings` class in the backend that validates environment on startup
- `DATABASE_URL` and `OPENROUTER_API_KEY` will fail silently if missing
- `LLM_MOCK` and `MASSIVE_API_KEY` have no type coercion

**Impact:**
- Startup errors are cryptic ("connection failed" instead of "DATABASE_URL not set")
- Type coercion could fail (e.g., `LLM_MOCK=yes` instead of `true`)

**Fix approach:**
- Create `backend/app/settings.py` with a Pydantic Settings class
- Validate all required vars on app startup
- Use in FastAPI app initialization to fail fast with clear error messages

---

## Code Debt

### Simulator: GBM Math Precision

**Issue:** Prices are kept at full float precision internally but rounded to 2 decimals on output.

**Files:** `backend/app/market/simulator.py` (lines 119, 149)

**Details:**
- Line 106: `diffusion = sigma * math.sqrt(self._dt) * float(z_correlated[i])` — full precision
- Line 107: `self._prices[ticker] *= math.exp(drift + diffusion)` — accumulated error
- Line 119: `round(self._prices[ticker], 2)` — final rounding for display

**Risk:**
- Accumulated floating-point error over 1000s of iterations could diverge from true GBM path
- Line 117 floor at $0.01 is a band-aid for extreme edge cases

**Current status:** Acceptable for a simulator. Real market data uses broker precision. Tests pass.

**Recommendation:** Monitor for price divergence over extended runs (48+ hours). If needed, use `Decimal` for precision or track price per-tick error.

---

### Massive Client: Timestamp Conversion is Fragile

**Issue:** Assumes Massive API always returns milliseconds; no validation.

**Files:** `backend/app/market/massive_client.py` (line 116)

```python
timestamp = snap.last_trade.timestamp / 1000.0
```

**Risk:**
- If Massive changes to returning seconds, all timestamps will be wrong (1000x off)
- No fallback if field is missing or None
- Error handling is generic (caught in line 128, logged, and skipped)

**Fix approach:**
- Add explicit validation: if timestamp > 1e12, assume ms; else assume seconds
- Add a test case for both timestamp formats
- Consider using `snapshot.last_trade.sip_timestamp` if available (more reliable)

---

### Synchronous REST Client in Thread Pool

**Issue:** Massive client uses `asyncio.to_thread()` to run synchronous REST calls.

**Files:** `backend/app/market/massive_client.py` (line 111)

```python
snapshots = await asyncio.to_thread(self._fetch_snapshots)
```

**Considerations:**
- This is **correct** — avoids blocking the event loop
- PriceCache uses `threading.Lock` because of this design
- However, thread pool is shared across the entire app — contention possible if other services use it

**Scaling concern:** If the backend grows to handle many concurrent tasks (LLM inference, database queries), the thread pool may become bottleneck. Monitor for thread pool saturation in production.

---

## Security Considerations

### Ticker Validation Not Implemented

**Issue:** The PLAN specifies that tickers should be validated to 1–5 uppercase alpha characters, but no validation layer exists.

**Files:** None — this validation hasn't been written yet (will be in portfolio/watchlist endpoints)

**Risk:**
- SQL injection if ticker is used in raw SQL (unlikely with ORM, but possible)
- XSS if ticker is displayed without escaping
- Watchlist bloat if arbitrary strings are accepted

**Fix approach:**
- Add a Pydantic validator for ticker field: `^[A-Z]{1,5}$`
- Apply trim and uppercase on input
- Reject non-conforming tickers with 400 Bad Request
- Document in API schema

---

### API Error Responses: Consistent Format Missing

**Issue:** Error response format is defined in PLAN.md but not implemented in code.

**Files:** None — backend endpoints don't exist yet

**Plan specifies:**
```json
{"error": "Short message", "detail": "Longer explanation"}
```

**Fix approach:**
- Create a Pydantic `ErrorResponse` model
- Use FastAPI exception handlers to return this format consistently
- Document all error codes in OpenAPI schema

---

### No Rate Limiting

**Issue:** If an SSE endpoint or API endpoint is exposed without rate limiting, malicious actors could flood it.

**Files:** Not applicable yet (no endpoints exist), but should be added before public deployment

**Recommendation:**
- Add FastAPI `slowapi` middleware for rate limiting
- Limit to 10 requests/second per IP for most endpoints
- Limit SSE reconnections to 1 per second (standard)
- Log rate limit violations

---

## Testing Gaps

### Market Data Stream: Version Counter Race Condition (Unlikely but Possible)

**Issue:** SSE generator reads `cache.version` in a loop. If a price update happens between reads, a version bump could be missed.

**Files:** `backend/app/market/stream.py` (lines 86–87)

```python
current_version = price_cache.version
if current_version != last_version:
```

**Why it's unlikely:** The loop checks every 500ms and the cache updates at 500ms (simulator) or 15s (Massive), so the window is narrow.

**Why it could still happen:** If many rapid updates occur while the SSE task is suspended, one could be skipped.

**Fix approach:**
- This is actually **NOT a bug** because version is monotonically increasing. Once incremented, it will always be different from `last_version`, so no updates are truly "lost" — they're just batched.
- If strict delivery guarantees are needed (e.g., for trading), consider an event queue instead of version-based change detection.

**Current status:** Safe for MVP.

---

### LLM Integration: Structured Output Fallback Untested

**Issue:** PLAN.md section 9 specifies: "Retry once, then return fallback error message with no actions."

**Files:** Not implemented yet (backend/app/llm/ doesn't exist)

**Concern:** What does the fallback look like? How does the frontend display it?

**Fix approach:**
- When structured output parsing fails, return:
  ```json
  {
    "message": "I encountered an error processing your request. Please try again.",
    "trades": [],
    "watchlist_changes": []
  }
  ```
- Add unit tests for malformed LLM responses
- Document retry behavior in chat message context (optional: show "Retry" button)

---

## Frontend Concerns (Architectural)

### Chart Library Not Selected

**Issue:** PLAN.md recommends "Lightweight Charts" but no dependency is specified.

**Files:** Not applicable (frontend doesn't exist yet)

**Risk:**
- Lightweight Charts is ~30 KB gzipped (good)
- Recharts is ~40 KB but more feature-rich
- TradingView's lightweight-charts has GPL-style licensing (check before use)

**Recommendation:** Use `lightweight-charts` npm package (by TradingView, Apache 2.0 license).

---

### Price Flash Animation: CSS Performance

**Issue:** Flashing every price change with CSS transitions could cause jank on slower devices.

**Files:** Not applicable yet, but important for implementation

**Concern:** With 10 tickers updating every 500ms, that's 10 DOM mutations per tick × 60fps = potential for dropped frames.

**Recommendation:**
- Use CSS `will-change: background-color` to hint to the browser
- Use `transition: background-color 500ms ease-out` (no other properties)
- Benchmark on low-end mobile device
- Consider debouncing updates (batch every 1 second) if jank occurs

---

### Sparkline Mini-Charts: Memory Overhead

**Issue:** Accumulating price data "since page load" could grow unbounded.

**Files:** Not applicable yet

**Concern:** A watchlist of 10 tickers with updates every 500ms = 1,200 data points per hour × 10 = 12K points in memory. Over a week, this is 2M+ points.

**Recommendation:**
- Cap the sparkline history to the last 2 hours (14,400 points max)
- Implement a rolling window: discard oldest point when size exceeds limit
- Consider server-side aggregation (e.g., send OHLC bars instead of tick data)

---

## Operational Concerns

### No Monitoring or Health Checks

**Issue:** No health check endpoint, logging, or error tracking.

**Files:**
- `/api/health` not implemented
- No logging configuration for production

**Impact:**
- Docker Compose cannot verify service health (health checks optional in compose)
- No way to diagnose failures in production
- No error aggregation or alerting

**Fix approach:**
- Add `GET /api/health` endpoint that returns `{"status": "ok"}`
- Include last price update timestamp
- Add structured logging (JSON format for ECS/CloudWatch)
- Add error tracking (Sentry or similar for production)

---

### No Database Backups Specified

**Issue:** Using Neon serverless Postgres but no backup strategy documented.

**Files:** Not applicable (database layer not implemented)

**Current assumption:** Neon handles backups automatically (they do).

**Recommendation:** Document backup retention in `planning/` folder and add restore procedure to runbooks.

---

## Dependencies at Risk

### massive (Polygon.io SDK): Tied to One API

**Status:** `massive>=1.0.0` is a required dependency but optional in functionality (can use simulator instead).

**Files:** `backend/pyproject.toml` (line 14)

**Risk:**
- If Massive/Polygon.io API changes, library must be updated
- If Polygon.io shuts down, feature becomes unavailable (simulator still works)

**Mitigation:** Already in place — simulator is default, Massive is optional.

**No action needed.**

---

### numpy: GBM Math Dependency

**Status:** `numpy>=2.0.0` required for Cholesky decomposition.

**Files:**
- `backend/pyproject.toml` (line 13)
- `backend/app/market/simulator.py` (line 22, import; line 173, np.linalg.cholesky)

**Risk:**
- NumPy is a mature library but heavy (adds ~30 MB to Docker image)
- Could be replaced with pure Python (scipy.linalg or manual Cholesky)

**Cost/benefit:** For an MVP, the simplicity of NumPy outweighs the size. Revisit if image size becomes an issue.

**No action needed.**

---

## Summary Table

| Concern | Severity | Component | Status |
|---------|----------|-----------|--------|
| Missing backend services (portfolio, LLM, chat) | **CRITICAL** | Architecture | Not started |
| Frontend directory empty | **CRITICAL** | Architecture | Not started |
| Docker Compose / Dockerfiles missing | **CRITICAL** | Deployment | Not started |
| E2E tests missing | **CRITICAL** | Testing | Not started |
| Ticker validation | High | API | Not started |
| Error response format | High | API | Not started |
| Massive API: delayed updates (15s) | Medium | Market Data | By design |
| GBM correlation assumptions | Medium | Simulator | Documented |
| Timestamp conversion fragility | Medium | API Client | Needs validation |
| Health check endpoint | Medium | Operations | Not started |
| Rate limiting | Medium | Security | Not started |
| Chart library selection | Low | Frontend | Recommended |
| Sparkline memory overhead | Low | Frontend | Needs design |

---

*Concerns audit: 2026-03-01*
