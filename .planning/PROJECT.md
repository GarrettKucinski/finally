# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. This is the capstone project for an agentic AI coding course, built entirely by coding agents.

## Core Value

Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that can both analyze and execute trades — all in a single, polished dark-themed terminal UI.

## Requirements

### Validated

- ✓ Market data simulator with GBM and correlated moves — existing
- ✓ Massive API client for real market data (optional) — existing
- ✓ Abstract market data interface (strategy pattern) — existing
- ✓ Thread-safe price cache — existing
- ✓ SSE streaming endpoint (`/api/stream/prices`) — existing
- ✓ Environment-gated data source factory — existing
- ✓ Backend project structure (FastAPI + uv) — existing

### Active

- [ ] Database layer: Neon Postgres schema, connection pool, seed data
- [ ] Portfolio API: positions, cash balance, total value, unrealized P&L
- [ ] Trade execution: market orders, validation (cash/shares), instant fill
- [ ] Portfolio history: snapshots every 30s + after trades, 24h retention
- [ ] Watchlist CRUD: add/remove tickers, return tickers with live prices
- [ ] LLM chat integration: LiteLLM → OpenRouter (Cerebras), structured outputs
- [ ] AI auto-execution: trades and watchlist changes from LLM responses
- [ ] Chat persistence: last 20 messages, actions stored as JSONB
- [ ] Health check endpoint
- [ ] Next.js frontend: dark terminal aesthetic, Tailwind CSS
- [ ] Watchlist panel: live prices, flash animations, sparkline charts
- [ ] Main chart area: selected ticker detail chart (Lightweight Charts)
- [ ] Portfolio heatmap: treemap sized by weight, colored by P&L
- [ ] P&L chart: portfolio value over time
- [ ] Positions table: ticker, qty, avg cost, current price, unrealized P&L
- [ ] Trade bar: ticker/quantity inputs, buy/sell buttons
- [ ] AI chat panel: collapsible sidebar, message history, loading state, inline action confirmations
- [ ] Header: portfolio total value (live), connection status dot, cash balance
- [ ] SSE client: EventSource connection with auto-reconnect
- [ ] Docker: Dockerfiles for frontend + backend, docker-compose.yml
- [ ] E2E tests: Playwright in docker-compose.test.yml with LLM_MOCK=true

### Out of Scope

- User authentication/login — single pre-seeded default user for v1
- Limit orders / order book — market orders only, dramatically simpler
- Real-time chat streaming — Cerebras is fast enough, loading indicator sufficient
- Mobile-native app — web desktop-first, functional on tablet
- Cloud deployment (Terraform/App Runner) — stretch goal, not core build
- WebSockets — SSE is sufficient for one-way server→client push
- Docker volumes — all persistent data in Neon Postgres

## Context

**Existing codebase:** The market data subsystem is complete with 113 passing tests and 96% line coverage. It includes a GBM simulator, Massive API client, price cache, SSE streaming, and factory pattern — all behind an abstract interface. The backend is a uv-managed FastAPI project. The frontend directory is empty.

**Tech stack (locked):** FastAPI (Python 3.12, uv) backend, Next.js (TypeScript) frontend, Neon serverless Postgres, SSE for real-time data, LiteLLM → OpenRouter (Cerebras) for AI, Docker Compose for orchestration.

**Visual design:** Dark Bloomberg-terminal aesthetic. Backgrounds ~`#0d1117`, accent yellow `#ecad0a`, blue primary `#209dd7`, purple secondary `#753991`. Price flash animations (green/red fade over ~500ms). Desktop-first, data-dense layout.

**Market data behavior:** Simulator uses GBM with correlated moves and random events. Updates ~500ms. Massive API polls on configurable interval (15s free tier). Both write to shared price cache; SSE reads from cache.

**Database:** Neon serverless Postgres via `DATABASE_URL`. Tables: users, users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages. Auto-init on startup via FastAPI lifespan. Default user pre-seeded with $10,000 cash and 10 watchlist tickers.

**LLM integration:** Uses LiteLLM via OpenRouter with Cerebras inference. Structured output schema returns message + optional trades + optional watchlist_changes. Auto-executes trades (simulated money, zero stakes). Mock mode (`LLM_MOCK=true`) for testing.

## Constraints

- **Tech stack**: FastAPI + Next.js + Neon Postgres + Docker Compose — all locked per PLAN.md
- **Single user**: No auth for v1, default user pre-seeded — all tables FK to users(id)
- **Market orders only**: No limit orders, no order book, instant fill at cached price
- **No CORS needed**: Next.js rewrites proxy `/api/*` to backend — single user-facing port 3000
- **Charting**: Lightweight Charts for main chart area
- **AI model**: `openrouter/openai/gpt-oss-120b` via LiteLLM with Cerebras inference provider

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push is all we need; simpler, universal browser support | — Pending |
| Next.js rewrites for API proxy | No CORS, single user-facing port, transparent to client code | — Pending |
| Neon serverless Postgres | Persistent data without Docker volumes, proper SQL types, free tier | — Pending |
| Market orders only | Eliminates order book complexity, dramatically simpler portfolio math | — Pending |
| LLM auto-execution | Simulated environment, zero stakes, impressive demo, agentic AI showcase | — Pending |
| Lightweight Charts | Canvas-based, performant for real-time financial data | — Pending |
| uv for Python | Fast, modern, reproducible lockfile | ✓ Good |
| Strategy pattern for market data | Clean abstraction, both sources interchangeable | ✓ Good |

---
*Last updated: 2026-03-01 after initialization*
