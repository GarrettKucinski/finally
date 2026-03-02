# Project Research Summary

**Project:** FinAlly — AI Trading Workstation
**Domain:** Real-time financial data dashboard with AI-powered agentic trading
**Researched:** 2026-03-01
**Confidence:** HIGH

## Executive Summary

FinAlly is a brownfield project with the market data subsystem already complete and production-proven (FastAPI 0.115+, Python 3.12, uv, asyncpg, SSE streaming, 113 tests at 96% coverage). The remaining build covers five areas: database initialization, portfolio/trade APIs, LLM chat integration, Next.js frontend, and Docker orchestration. The recommended approach follows a strict dependency chain — database first, then backend APIs, then LLM chat (which depends on trade execution), then frontend, then Docker/E2E. The architecture is a layered service pattern: route handlers delegate to plain async service functions that accept pool and cache as arguments, keeping services testable without framework coupling.

The key technical risks are concentrated in two areas. First, the LiteLLM + OpenRouter structured output bug (GitHub issues #10465, #13438) requires using `extra_body` instead of `response_format` — this is a known issue with a clear workaround but must be implemented correctly from the start. Second, frontend performance at 500ms update intervals across 10+ tickers will cause render storms without Zustand selector-based subscriptions per ticker. Both risks are well-understood and have documented mitigation strategies. The Neon Postgres connection pooler also requires `statement_cache_size=0` on pool creation — missing this causes intermittent production failures.

The differentiating feature of FinAlly is AI auto-execution without confirmation dialogs. This is rare in the market (no direct competitors do zero-confirmation auto-execution in a simulated environment) and creates the demo's "wow factor." The visual differentiators — portfolio heatmap treemap, sparkline mini-charts in the watchlist, and the Bloomberg-inspired dark terminal aesthetic — elevate the project from paper trading simulator to professional-grade workstation. Anti-features are as deliberate as features: no limit orders, no auth, no backtesting, no token streaming. Every omission keeps scope achievable.

---

## Key Findings

### Recommended Stack

The backend stack is locked by the existing market data layer and should not change. The critical additions are the asyncpg connection pool (with `statement_cache_size=0` for Neon) and LiteLLM 1.81+ for OpenRouter integration. For the frontend, Next.js 15.x LTS is recommended over 16.x (breaking changes with zero benefit for this project). Zustand 5.x is essential — React Context cannot handle 50+ re-renders/second from SSE price updates. Lightweight Charts 5.1.0 is locked per the project plan. For the portfolio heatmap, `@nivo/treemap` 0.99.x is recommended over direct D3 or ECharts due to React integration and bundle size.

**Core technologies:**
- FastAPI 0.115+ / Python 3.12 / uv: backend framework — locked, proven in production
- asyncpg 0.31.0+ / Neon Postgres: database — `statement_cache_size=0` required for pooled endpoint
- LiteLLM 1.81+ via OpenRouter: LLM integration — use `extra_body` workaround for structured output
- Next.js 15.x LTS: frontend framework — avoid 16.x breaking changes
- Zustand 5.x: state management — selector subscriptions prevent SSE re-render storms
- Lightweight Charts 5.1.0: charting — locked per plan, canvas-based for performance
- @nivo/treemap 0.99.x: portfolio heatmap — React-native, lighter than ECharts
- Tailwind CSS v4: styling — CSS-first config, 70% smaller output than v3
- Native EventSource API: SSE client — no library needed, singleton via Zustand

### Expected Features

**Must have (table stakes):**
- Real-time price streaming with green/red flash animations — baseline expectation of any trading tool
- Portfolio dashboard with positions table (ticker, qty, avg cost, current price, P&L) — most-visited view
- Trade execution (buy/sell market orders, instant fill) — the core verb of the platform
- Watchlist management (add/remove tickers) — personalization baseline
- Trade history log — users need to verify what happened
- Connection status indicator (green/yellow/red dot in header) — liveness signal for real-time data
- Dark terminal-style theme (#0d1117 background) — aesthetic IS the product identity
- Consistent error handling — silent errors destroy trust

**Should have (differentiators):**
- AI chat assistant with natural language auto-execution — the killer feature, agentic AI with zero confirmation
- Portfolio heatmap treemap — found in Bloomberg/Finviz but almost never in paper trading simulators
- Sparkline mini-charts in watchlist — information density signal of "professional tool"
- P&L chart (portfolio value over time from snapshots) — transforms static number into narrative
- Detailed ticker chart (click-to-expand from watchlist) — cohesive terminal workflow
- AI actions displayed inline in chat (structured cards, not just text) — visual proof of agentic capability

**Defer (v2+):**
- User authentication and multi-user support — schema supports it (user_id columns), but no login for v1
- Limit orders, stop-loss, advanced order types — requires order book and matching engine
- Historical price data and backtesting — fundamental architecture change
- Options, futures, crypto — separate asset class complexity
- Mobile-first layout — desktop terminal is the target
- Token-by-token LLM streaming — incompatible with structured output auto-execution

### Architecture Approach

The system uses a layered service architecture on top of the existing market data layer. FastAPI lifespan is the single orchestration point: it creates the asyncpg pool, initializes schema, seeds default data, starts market data source with DB-loaded watchlist tickers, wires background tasks (snapshot recorder, snapshot cleanup), and attaches pool/cache/source to `app.state` for route handlers to consume. Services are plain async functions — not classes — that accept pool and cache as arguments, making them trivially testable. The watchlist service must update both the database and the live market source atomically to keep the SSE stream synchronized with the user's watchlist.

**Major components:**
1. Database layer (`db.py`) — asyncpg pool creation, schema init via `CREATE TABLE IF NOT EXISTS`, seed defaults
2. Portfolio service (`portfolio_service.py`) — trade execution with DB transactions, P&L calculation, snapshot recording
3. Watchlist service (`watchlist_service.py`) — CRUD with dual update (DB + market source)
4. Chat service (`chat_service.py`) — context building, LiteLLM call, structured output parsing, auto-execution pipeline
5. Frontend Zustand store — singleton SSE connection, per-ticker selector subscriptions
6. Background tasks — 30s snapshot recorder, 24h snapshot cleanup, both cancelled on lifespan exit

### Critical Pitfalls

1. **Neon prepared statement cache (asyncpg)** — Always set `statement_cache_size=0` when using Neon's pooled endpoint. Missing this causes intermittent `prepared statement does not exist` errors in production that work fine locally.

2. **LiteLLM structured output bug** — Pass `response_format` via `extra_body`, not as a direct parameter. LiteLLM silently strips it for OpenRouter models. Test this integration first before building the auto-execution pipeline on top of it.

3. **SSE re-render storms (frontend)** — Use Zustand with per-ticker selectors (`useStore((s) => s.prices[ticker])`). React Context or whole-store subscriptions cause 50+ re-renders/second with 10 tickers at 500ms intervals.

4. **Race conditions in trade execution** — Wrap buy/sell logic in a database transaction with `SELECT ... FOR UPDATE` on the user profile row. Both manual trades and LLM-initiated trades must go through the same `execute_trade()` function — no separate paths.

5. **Average cost corruption on partial sells** — On sell, `avg_cost` stays unchanged; only `quantity` decreases. Recalculating avg_cost on sell corrupts remaining-position P&L. Delete the row when quantity reaches 0.

---

## Implications for Roadmap

Based on research, the dependency chain is clear and constraining. The suggested phase structure follows the build order identified in ARCHITECTURE.md, which is validated by the feature dependency map in FEATURES.md and the pitfall phase assignments in PITFALLS.md. All three research files converge on the same ordering.

### Phase 1: Database Foundation
**Rationale:** Everything downstream depends on the database. Portfolio APIs, trade execution, watchlist sync, LLM chat — none can be built without the pool, schema, and seed data. This is the prerequisite for all other phases.
**Delivers:** asyncpg pool in lifespan, `CREATE TABLE IF NOT EXISTS` for all 7 tables, default user seeded, `/api/health` endpoint with DB ping
**Addresses:** TS-2 (portfolio), TS-3 (trade execution), TS-4 (watchlist) all depend on this
**Avoids:** Pitfalls 1.1 (prepared statement cache), 1.2 (cold start), 1.3 (SSL), 7.4 (CORS dev setup)

### Phase 2: Portfolio and Watchlist APIs
**Rationale:** Trade execution and watchlist management are the core verbs of the platform. They must exist before LLM chat (which calls them for auto-execution) and before the frontend (which calls them for manual trades).
**Delivers:** `GET /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`, full watchlist CRUD, portfolio snapshot background task
**Addresses:** TS-2, TS-3, TS-4, TS-5 (trade history), D-4 (P&L chart data source)
**Uses:** asyncpg transactions, PriceCache integration, market source sync
**Avoids:** Pitfalls 1.4 (transactions), 2.1 (float rounding), 2.2 (avg cost formula), 7.1 (background task shutdown), 7.3 (watchlist sync)

### Phase 3: LLM Chat Integration
**Rationale:** Chat depends on trade execution (Phase 2) and watchlist management (Phase 2) for auto-execution. It's isolated enough to build as its own phase before the frontend is ready. The `extra_body` workaround must be validated early — it's the highest-risk integration.
**Delivers:** `POST /api/chat` with context building, LiteLLM structured output, auto-execution pipeline, chat message persistence, `LLM_MOCK=true` mode
**Addresses:** D-1 (AI chat), D-6 (AI actions inline — data structure defined here)
**Uses:** LiteLLM 1.81+ with `extra_body` workaround, Pydantic ChatResponse model
**Avoids:** Pitfalls 3.1 (LiteLLM OpenRouter bug), 3.2 (malformed JSON), 3.3 (hallucinated trades), 3.4 (context overflow), 7.2 (chat atomicity)

### Phase 4: Frontend Foundation
**Rationale:** The frontend can be scaffolded and styled before backend APIs are complete, but full integration requires working endpoints. SSE is already proven on the backend; the frontend hook is the new work.
**Delivers:** Next.js 15 + Tailwind v4 dark theme, SSE hook (`usePriceStream`) with Zustand store, watchlist panel with live prices + flash animations, trade bar (buy/sell), positions table, header (total value, cash, connection status)
**Addresses:** TS-1 (SSE frontend), TS-2, TS-3, TS-4, TS-6 (connection status), TS-7 (dark theme), TS-8 (error handling)
**Uses:** Zustand 5.x per-ticker selectors, native EventSource singleton
**Avoids:** Pitfalls 4.1 (SSE proxy buffering), 4.2 (thundering herd), 4.3 (EventSource cleanup), 5.1 (re-render storms), 5.2 (flash animation stacking)

### Phase 5: Frontend Visualizations and AI Chat Panel
**Rationale:** Visualizations and the chat panel build on the foundation from Phase 4. They require live price data and portfolio data to be flowing. These are the differentiating features — they can be deferred until the foundation is solid.
**Delivers:** Sparkline mini-charts (watchlist), detail chart (Lightweight Charts, click-to-expand), portfolio heatmap (@nivo/treemap), P&L chart (portfolio value over time), AI chat panel (messages, loading state, inline action cards)
**Addresses:** D-2 (heatmap), D-3 (sparklines), D-4 (P&L chart), D-5 (detail chart), D-6 (inline AI actions)
**Uses:** Lightweight Charts 5.1.0, @nivo/treemap 0.99.x
**Avoids:** Pitfalls 5.3 (chart memory leak), 5.4 (heatmap layout thrashing)

### Phase 6: Docker and E2E Tests
**Rationale:** Dockerfiles and E2E tests require both services to be complete and integrated. These are the final validation layer, not a prerequisite for anything.
**Delivers:** `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml` with healthcheck, `docker-compose.test.yml` with Playwright, E2E test scenarios, `.env.example`
**Addresses:** Full system integration, `LLM_MOCK=true` E2E testing
**Avoids:** Pitfalls 6.1 (depends_on readiness), 6.2 (build-time BACKEND_URL), 6.3 (env consistency)

### Phase Ordering Rationale

- Database must come before everything — no service can function without the pool and schema
- Portfolio APIs before LLM chat — chat auto-execution calls `execute_trade()` directly; that function must exist
- LLM chat before frontend chat panel — the API contract (structured response schema) must be settled before building the UI that consumes it
- Frontend foundation before visualizations — the Zustand store and SSE hook must be in place before charting components can subscribe to price data
- Docker/E2E last — validates the complete system; Playwright tests require both containers running
- Tailwind theme (TS-7) and connection status (TS-6) can proceed in parallel during frontend phases — pure styling and simple state

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (LLM Chat):** The `extra_body` structured output workaround needs early validation against the actual OpenRouter + Cerebras endpoint. System prompt engineering for reliable structured JSON output may require iteration. Consider a spike before full phase planning.
- **Phase 5 (Visualizations):** `@nivo/treemap` v0.99.x React 19 compatibility needs verification during scaffold. Lightweight Charts React integration pattern (direct useEffect vs wrapper library) needs a decision.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Database):** asyncpg + Neon is well-documented with official guides. Pitfalls are known and preventions are clear.
- **Phase 2 (Portfolio/Watchlist APIs):** Standard CRUD with transactions. Well-understood patterns.
- **Phase 4 (Frontend Foundation):** Next.js 15 + Tailwind v4 + Zustand are stable with extensive documentation.
- **Phase 6 (Docker/E2E):** Standard two-service Docker Compose with Playwright. Well-trodden pattern.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Backend locked and proven. Frontend choices (Next.js 15, Zustand, Nivo) have strong community consensus and official docs. One MEDIUM item: LiteLLM bug requires workaround. |
| Features | HIGH | Feature set directly specified in PLAN.md. Research confirms table-stakes vs differentiators split. No ambiguity about scope. |
| Architecture | HIGH | Existing market data layer provides proven integration points. Service layer pattern is standard FastAPI practice. Data flow diagrams are concrete and implementable. |
| Pitfalls | HIGH | Most pitfalls are documented bugs (GitHub issues) or well-known async Python patterns. Prevention strategies are specific and actionable. |

**Overall confidence:** HIGH

### Gaps to Address

- **LiteLLM `extra_body` workaround stability:** Issue #13438 may be fixed in a future LiteLLM release. Validate the workaround against the current version before building the full chat pipeline. If it's fragile, fall back to direct httpx calls to OpenRouter.
- **@nivo/treemap + React 19 compatibility:** Nivo 0.99.x should support React 19, but this needs a quick validation during frontend scaffolding before committing to the library.
- **Vitest vs Jest for Next.js 15 unit tests:** Either works; make the call during Phase 4 scaffolding based on what `create-next-app` defaults to.
- **Cerebras inference speed in practice:** The plan assumes Cerebras is fast enough that a loading indicator suffices instead of token streaming. Validate response latency against the actual endpoint during Phase 3.

---

## Sources

### Primary (HIGH confidence)
- Neon official docs — asyncpg `statement_cache_size=0`, pooled endpoint configuration, SSL requirements
- FastAPI official docs — lifespan events, `app.state` dependency injection pattern
- LiteLLM GitHub issues #10465, #13438 — `extra_body` structured output workaround for OpenRouter
- Next.js 15 official docs — App Router, rewrites configuration, TypeScript strict mode
- Zustand docs — selector subscriptions, singleton store pattern
- Lightweight Charts v5 docs — `series.update()` pattern, chart lifecycle

### Secondary (MEDIUM confidence)
- Community consensus on Zustand vs React Context for real-time data (multiple blog posts, Stack Overflow)
- @nivo/treemap npm page and GitHub — version compatibility with React
- Playwright Docker image pinning best practices

### Tertiary (LOW confidence)
- Cerebras inference latency estimates — based on general knowledge of fast inference providers, not benchmarked
- Nivo treemap React 19 compatibility — inferred from version numbers, not tested

---

*Research completed: 2026-03-01*
*Ready for roadmap: yes*
