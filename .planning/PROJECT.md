# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a fully functional AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades. It features a dark Bloomberg-terminal aesthetic with real-time price updates, portfolio visualizations, and an AI copilot sidebar. Built entirely by coding agents as the capstone project for an agentic AI coding course.

## Core Value

Users can watch live-streaming prices, trade a simulated portfolio, and chat with an AI assistant that can both analyze and execute trades — all in a single, polished dark-themed terminal UI.

## Requirements

### Validated

- ✓ Market data simulator with GBM and correlated moves — v1.0
- ✓ Massive API client for real market data (optional) — v1.0
- ✓ Abstract market data interface (strategy pattern) — v1.0
- ✓ Thread-safe price cache — v1.0
- ✓ SSE streaming endpoint (`/api/stream/prices`) — v1.0
- ✓ Environment-gated data source factory — v1.0
- ✓ Backend project structure (FastAPI + uv) — v1.0
- ✓ Database layer: Neon Postgres schema, connection pool, seed data — v1.0
- ✓ Portfolio API: positions, cash balance, total value, unrealized P&L — v1.0
- ✓ Trade execution: market orders, validation (cash/shares), instant fill — v1.0
- ✓ Portfolio history: snapshots every 30s + after trades, 24h retention — v1.0
- ✓ Watchlist CRUD: add/remove tickers, return tickers with live prices — v1.0
- ✓ LLM chat integration: LiteLLM → OpenRouter (Cerebras), structured outputs — v1.0
- ✓ AI trade proposals with user confirmation — v1.0
- ✓ Watchlist auto-execution from LLM responses — v1.0
- ✓ Chat persistence: last 20 messages, actions stored as JSONB — v1.0
- ✓ Health check endpoint — v1.0
- ✓ Next.js frontend: dark terminal aesthetic, Tailwind CSS — v1.0
- ✓ Watchlist panel: live prices, flash animations, sparkline charts — v1.0
- ✓ Main chart area: selected ticker detail chart (Lightweight Charts) — v1.0
- ✓ Portfolio heatmap: treemap sized by weight, colored by P&L — v1.0
- ✓ P&L chart: portfolio value over time — v1.0
- ✓ Positions table: ticker, qty, avg cost, current price, unrealized P&L — v1.0
- ✓ Trade bar: ticker/quantity inputs, buy/sell buttons — v1.0
- ✓ AI chat panel: collapsible sidebar, message history, loading state, inline action cards — v1.0
- ✓ Header: portfolio total value (live), connection status dot, cash balance — v1.0
- ✓ SSE client: EventSource connection with auto-reconnect — v1.0
- ✓ Docker: Dockerfiles for frontend + backend, docker-compose.yml — v1.0
- ✓ E2E tests: Playwright in docker-compose.test.yml with LLM_MOCK=true — v1.0

### Active

(None — v1.0 shipped. Use `/gsd:new-milestone` for v2 requirements.)

### Out of Scope

- User authentication/login — single pre-seeded default user for v1
- Limit orders / order book — market orders only, dramatically simpler
- Real-time chat streaming — Cerebras is fast enough, loading indicator sufficient
- Mobile-native app — web desktop-first, functional on tablet
- Cloud deployment (Terraform/App Runner) — stretch goal, not core build
- WebSockets — SSE is sufficient for one-way server→client push
- Docker volumes — all persistent data in Neon Postgres

## Context

**Shipped v1.0:** 7 phases, 15 plans, 53 requirements satisfied. 1,836 LOC TypeScript (frontend), 2,298 LOC Python (backend). 124 git commits over 24 days.

**Tech stack (locked):** FastAPI (Python 3.12, uv) backend, Next.js (TypeScript) frontend, Neon serverless Postgres, SSE for real-time data, LiteLLM → OpenRouter (Cerebras) for AI, Docker Compose for orchestration.

**Visual design:** Dark Bloomberg-terminal aesthetic. Backgrounds ~`#0d1117`, accent yellow `#ecad0a`, blue primary `#209dd7`, purple accent `#753991`. Price flash animations (green/red fade over ~500ms). Desktop-first, data-dense layout.

**Known tech debt (6 items, no blockers):**
- CHAT-05: Trades user-confirmed instead of auto-executed (deliberate improvement)
- VIZ-01: Change% baseline is tick-to-tick, not seed-price
- Stale CORS middleware and stub comment (cosmetic)
- WatchlistPanel useEffect dependency loop (continuous polling)
- SSE Route Handler missing chunked encoding header

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
| SSE over WebSockets | One-way push is all we need; simpler, universal browser support | ✓ Good — works reliably, EventSource auto-reconnects |
| Next.js rewrites for API proxy | No CORS, single user-facing port, transparent to client code | ✓ Good — SSE required Route Handler proxy workaround |
| Neon serverless Postgres | Persistent data without Docker volumes, proper SQL types, free tier | ✓ Good — zero-config persistence |
| Market orders only | Eliminates order book complexity, dramatically simpler portfolio math | ✓ Good — kept scope manageable |
| Trade proposals (not auto-execute) | Safer UX; user confirms trades via ProposedTradeCard | ✓ Good — diverged from spec, better UX |
| Lightweight Charts | Canvas-based, performant for real-time financial data | ✓ Good — smooth real-time rendering |
| uv for Python | Fast, modern, reproducible lockfile | ✓ Good |
| Strategy pattern for market data | Clean abstraction, both sources interchangeable | ✓ Good |
| Recharts for portfolio viz | Treemap for heatmap, AreaChart for P&L | ✓ Good — declarative, React-native |
| SSE via Route Handler proxy | Avoid EventSource CORS issues in Docker | ✓ Good — solved buffering problem |

---
*Last updated: 2026-03-03 after v1.0 milestone*
