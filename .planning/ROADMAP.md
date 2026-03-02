# Roadmap: FinAlly -- AI Trading Workstation

## Overview

FinAlly is a brownfield project with the market data subsystem already complete (simulator, Massive API client, price cache, SSE streaming, 113 tests). The remaining build follows a strict dependency chain: database foundation first, then backend APIs (portfolio, watchlist), then LLM chat (which depends on trade execution for auto-execution), then the Next.js frontend in two phases (foundation then advanced visualizations), and finally Docker orchestration with E2E tests to validate the complete system.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Database Foundation** - Asyncpg pool, schema creation, seed data, and health check endpoint (completed 2026-03-02)
- [ ] **Phase 2: Portfolio & Watchlist APIs** - Trade execution, portfolio queries, watchlist CRUD, snapshot background tasks
- [ ] **Phase 3: LLM Chat Integration** - AI assistant with structured outputs, auto-execution pipeline, mock mode
- [x] **Phase 4: Frontend Foundation** - Next.js dark terminal UI, SSE client, watchlist with live prices, trade bar, positions table (completed 2026-03-02)
- [ ] **Phase 5: Visualizations & Chat Panel** - Sparklines, detail chart, portfolio heatmap, P&L chart, AI chat sidebar
- [ ] **Phase 6: Docker & E2E Tests** - Dockerfiles, docker-compose orchestration, Playwright E2E test suite

## Phase Details

### Phase 1: Database Foundation
**Goal**: Backend connects to Neon Postgres, initializes all tables, seeds default data, and exposes a health check -- enabling all downstream API work
**Depends on**: Nothing (first phase); existing market data layer is already complete
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Backend starts and connects to Neon Postgres without errors (asyncpg pool with `statement_cache_size=0`)
  2. All 7 database tables exist after startup (users, users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages)
  3. Default user is seeded with $10,000 cash and 10 watchlist tickers on first run, and seed is skipped on subsequent runs
  4. `GET /api/health` returns 200 with a successful DB connectivity check
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Settings, DB pool lifecycle, SQL schema, seed data, FastAPI app with lifespan
- [ ] 01-02-PLAN.md — Health check endpoint with DB connectivity verification

### Phase 2: Portfolio & Watchlist APIs
**Goal**: Users can execute trades, view their portfolio with P&L, manage their watchlist, and the system records portfolio snapshots over time -- the core verbs of the trading platform
**Depends on**: Phase 1
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, PORT-08, PORT-09, PORT-10, PORT-11, WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05
**Success Criteria** (what must be TRUE):
  1. `GET /api/portfolio` returns the user's positions with current prices, unrealized P&L, cash balance, and total portfolio value
  2. User can buy shares (cash decreases, position created/updated) and sell shares (cash increases, position updated or deleted at zero quantity) via `POST /api/portfolio/trade`
  3. Buy with insufficient cash and sell with insufficient shares are rejected with clear error messages
  4. Portfolio snapshots are recorded every 30 seconds and immediately after each trade, with snapshots older than 24 hours cleaned up automatically
  5. Watchlist CRUD works end-to-end: adding a ticker registers it with the market data source (prices start streaming), removing it unregisters it (prices stop)
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Pydantic models, portfolio service (trade execution, P&L), portfolio & history routes
- [ ] 02-02-PLAN.md — Watchlist CRUD with market data sync, background snapshot tasks, lifespan wiring

### Phase 3: LLM Chat Integration
**Goal**: Users can chat with an AI assistant that understands their portfolio, suggests and executes trades, and manages their watchlist through natural language
**Depends on**: Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09
**Success Criteria** (what must be TRUE):
  1. `POST /api/chat` accepts a user message and returns a structured JSON response containing the assistant's message plus any trades and watchlist changes
  2. The LLM receives full portfolio context (cash, positions with P&L, watchlist with live prices, total value) and the last 20 messages of conversation history
  3. Trades and watchlist changes specified by the LLM are auto-executed through the same code paths as manual operations, with failures reported in the response
  4. Chat messages and executed actions are persisted to the database (retrievable across sessions)
  5. When `LLM_MOCK=true`, deterministic mock responses are returned without calling OpenRouter (enabling testing without an API key)
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md -- Chat models, service (context, history, mock mode, persistence), route handler, main.py wiring
- [ ] 03-02-PLAN.md -- Real LLM call via LiteLLM/Cerebras, trade and watchlist auto-execution, error collection

### Phase 4: Frontend Foundation
**Goal**: Users see a dark, data-dense trading terminal with live-streaming prices, can interact with their watchlist, execute trades, and monitor positions -- the core interactive experience
**Depends on**: Phase 1, Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, VIZ-01, VIZ-06, VIZ-07, VIZ-08
**Success Criteria** (what must be TRUE):
  1. Next.js app renders a dark terminal aesthetic (background ~`#0d1117`) with Tailwind CSS using accent colors (yellow, blue, purple)
  2. Prices stream live from the backend via SSE and the watchlist panel shows each ticker with current price, change %, and green/red flash animations on price updates
  3. Connection status indicator in the header shows green (connected), yellow (reconnecting), or red (disconnected) reflecting the actual SSE connection state
  4. User can buy and sell shares using the trade bar, see their positions update in the positions table (ticker, qty, avg cost, current price, P&L), and see cash/total value update in the header
  5. API errors display as toast or inline messages without crashing the UI, and all API calls use relative `/api/*` paths proxied through Next.js rewrites
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md -- Next.js scaffold, dark theme, Zustand stores, SSE hook, typed API client
- [x] 04-02-PLAN.md -- UI components: Header, WatchlistPanel, PositionsTable, TradeBar, Dashboard layout
- [ ] 04-03-PLAN.md -- Gap closure: SSE through Next.js rewrites (UI-07), sparkline mini-charts (VIZ-01)

### Phase 5: Visualizations & Chat Panel
**Goal**: Users experience the differentiating features -- sparkline mini-charts, a detailed ticker chart, portfolio heatmap, P&L history chart, and an AI chat sidebar with inline action cards
**Depends on**: Phase 3, Phase 4
**Requirements**: VIZ-02, VIZ-03, VIZ-04, VIZ-05, VIZ-09, VIZ-10
**Success Criteria** (what must be TRUE):
  1. Sparkline mini-charts in the watchlist accumulate price data from SSE since page load and render progressively
  2. Clicking a ticker in the watchlist opens a detailed Lightweight Charts view in the main chart area
  3. Portfolio heatmap (treemap) displays positions sized by portfolio weight and colored by P&L (green for profit, red for loss)
  4. P&L chart shows total portfolio value over time as a line chart using portfolio snapshot data
  5. AI chat panel (collapsible sidebar) allows sending messages, shows scrolling conversation history with loading state, and renders AI-executed trades and watchlist changes as structured visual cards inline
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Docker & E2E Tests
**Goal**: The entire application runs from a single `docker compose up` command and is validated by automated end-to-end tests
**Depends on**: Phase 4, Phase 5
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06, OPS-07
**Success Criteria** (what must be TRUE):
  1. `docker compose up` builds and starts both frontend and backend containers, with the frontend accessible at `http://localhost:3000` and the backend at `http://localhost:8000`
  2. Frontend proxies `/api/*` to the backend via Next.js rewrites within Docker networking (no CORS needed, single user-facing port)
  3. Playwright E2E tests run against the containerized app (via `docker-compose.test.yml`) with `LLM_MOCK=true` and cover core user flows (watchlist, trading, portfolio, chat)
  4. `.env.example` is committed with all required and optional environment variables documented
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Database Foundation | 0/2 | Complete    | 2026-03-02 |
| 2. Portfolio & Watchlist APIs | 1/2 | In Progress | - |
| 3. LLM Chat Integration | 0/2 | Not started | - |
| 4. Frontend Foundation | 2/2 | Complete | 2026-03-02 |
| 5. Visualizations & Chat Panel | 0/3 | Not started | - |
| 6. Docker & E2E Tests | 0/2 | Not started | - |
