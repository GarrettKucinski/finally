# Stack Research: AI Trading Workstation

> Research dimension: Stack
> Project: FinAlly -- AI Trading Workstation
> Context: Brownfield -- market data subsystem complete (FastAPI + uv + asyncpg). Researching remaining stack for database layer, portfolio APIs, LLM integration, Next.js frontend, and Docker orchestration.
> Date: 2026-03-01

---

## Executive Summary

The existing backend (FastAPI 0.115+, Python 3.12, uv) is solid and locked. The key decisions for the remaining build are: **Next.js 15.x LTS** (not 16.x — breaking changes, zero benefit), **Zustand** for frontend state (selector-based subscriptions prevent SSE re-render storms), **Tailwind CSS v4** with CSS-first config, **@nivo/treemap** for the portfolio heatmap, and careful handling of the **LiteLLM + OpenRouter structured output bug** (must use `extra_body` workaround).

---

## Backend Stack (Existing + Additions)

### Core Framework — FastAPI 0.115+ (LOCKED)

- **Status:** Already in production with 113 tests, 96% coverage
- **No changes needed** — existing market data subsystem proves the stack works
- **Confidence:** HIGH

### Database — asyncpg 0.31.0 + Neon Serverless Postgres

| Attribute | Detail |
|-----------|--------|
| Library | asyncpg 0.31.0+ (already in pyproject.toml as 0.29.0+, update to latest) |
| Connection | Neon pooled endpoint with `statement_cache_size=0` |
| SSL | `ssl="require"` in `create_pool()` |
| Why asyncpg | Already a dependency. Raw SQL preferred over ORM for this project — simpler, faster, no migration framework needed |
| Why NOT SQLAlchemy | Adds ORM complexity for 7 simple tables with straightforward queries. The plan specifies raw SQL schema init via `CREATE TABLE IF NOT EXISTS` |
| **Confidence** | HIGH — Official Neon docs + asyncpg verified |

**Critical notes:**
- Use Neon's **pooled** connection endpoint (PgBouncer in transaction mode)
- Set `statement_cache_size=0` to avoid prepared statement cache conflicts
- Set generous timeouts for cold start: `timeout=30, command_timeout=30`
- Avoid `SET` statements (transaction mode drops them)

### LLM Integration — LiteLLM 1.81+ via OpenRouter (Cerebras)

| Attribute | Detail |
|-----------|--------|
| Library | litellm 1.81.11+ |
| Model | `openrouter/openai/gpt-oss-120b` (Cerebras inference) |
| API Key | `OPENROUTER_API_KEY` env var |
| Why LiteLLM | Unified interface, handles OpenRouter routing, supports structured output (with workaround) |
| **Confidence** | MEDIUM — Known bug with structured output requires workaround |

**Known bug (LiteLLM GitHub #10465, #13438):**
LiteLLM's `supports_response_schema` returns `False` for OpenRouter models. The `response_format` parameter gets silently stripped. **Workaround:** Use `extra_body` to pass schema directly:

```python
response = await litellm.acompletion(
    model="openrouter/openai/gpt-oss-120b",
    messages=messages,
    extra_body={
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "chat_response", "schema": schema_dict}
        }
    },
)
```

**Fallback option:** Call OpenRouter directly via httpx if LiteLLM workaround is fragile.

### Testing — pytest 8.3+ (LOCKED)

- **Status:** Already configured with pytest-asyncio and pytest-cov
- **No changes needed**
- **Confidence:** HIGH

---

## Frontend Stack (New)

### Framework — Next.js 15.x LTS

| Attribute | Detail |
|-----------|--------|
| Version | 15.x (latest stable LTS) |
| Why NOT 16.x | Next.js 16 (Dec 2025) has breaking changes: middleware renamed to proxy.ts, Turbopack default, async params mandatory, cache model overhaul. Zero benefit for this project, high migration risk. |
| TypeScript | Yes, strict mode |
| Router | App Router (default in 15.x) |
| Rewrites | `next.config.ts` proxies `/api/*` to `BACKEND_URL` |
| **Confidence** | HIGH — Official docs, stable LTS |

### Styling — Tailwind CSS v4

| Attribute | Detail |
|-----------|--------|
| Version | 4.x (CSS-first config, no tailwind.config.js needed) |
| Config | `@theme` CSS variables in `globals.css` for FinAlly dark theme |
| Benefits | 70% smaller output than v3, native CSS cascade layers |
| Theme colors | `--color-bg: #0d1117`, `--color-accent-yellow: #ecad0a`, `--color-blue: #209dd7`, `--color-purple: #753991` |
| **Confidence** | HIGH |

### State Management — Zustand 5.x

| Attribute | Detail |
|-----------|--------|
| Version | 5.x (latest) |
| Why Zustand | 3KB bundle, selector-based subscriptions prevent re-render storms from 500ms SSE updates |
| Why NOT React Context | Context re-renders ALL consumers on any change. With 10+ tickers updating every 500ms, this causes 50+ re-renders/second |
| Why NOT Redux | Overkill for this scope. Zustand provides the same selector pattern with zero boilerplate |
| Why NOT Jotai | Zustand's centralized store is simpler for this use case (single price cache store) |
| Pattern | `useStore((s) => s.prices[ticker])` — per-ticker subscriptions |
| **Confidence** | HIGH — Community consensus for real-time data apps |

### Charting — Lightweight Charts 5.1.0 (LOCKED per PLAN.md)

| Attribute | Detail |
|-----------|--------|
| Version | 5.1.0 (latest on npm) |
| React wrapper | `lightweight-charts-react-wrapper` or direct useEffect integration |
| Usage | Main detail chart + sparkline mini-charts in watchlist |
| **Confidence** | HIGH — Locked per plan, verified on npm |

### Portfolio Heatmap — @nivo/treemap

| Attribute | Detail |
|-----------|--------|
| Version | 0.99.x (latest) |
| Why @nivo | Purpose-built D3 treemap, React-native, supports canvas rendering for performance |
| Why NOT Recharts | Lacks proper treemap support |
| Why NOT ECharts | 300KB+ bundle overhead for one visualization |
| Why NOT D3 direct | Nivo provides React integration out of the box |
| **Confidence** | HIGH |

### SSE Client — Native EventSource API

| Attribute | Detail |
|-----------|--------|
| No library needed | Browser-native `EventSource` API with built-in reconnection |
| Pattern | Custom `usePriceStream()` hook with useEffect cleanup |
| Singleton | Single EventSource instance shared across all components via Zustand store |
| **Confidence** | HIGH |

### Frontend Testing

| Attribute | Detail |
|-----------|--------|
| Unit/Component | React Testing Library (ships with create-next-app) |
| E2E | Playwright 1.58.2 (Docker image: `mcr.microsoft.com/playwright:v1.58.2-noble`) |
| E2E infra | `docker-compose.test.yml` in `test/` directory |
| E2E env | `LLM_MOCK=true` for deterministic testing |
| **Confidence** | MEDIUM — Version pinning critical for Playwright Docker |

---

## Docker Stack

### Containers

| Service | Base Image | Port |
|---------|-----------|------|
| frontend | node:20-slim | 3000 |
| backend | python:3.12-slim + uv | 8000 |

### Orchestration — Docker Compose

- `depends_on` with `condition: service_healthy` (backend healthcheck on `/api/health`)
- `env_file: .env` for backend
- Explicit `BACKEND_URL=http://backend:8000` for frontend
- No volumes needed (Neon handles persistence)

---

## What NOT to Use

| Technology | Why NOT |
|-----------|---------|
| Next.js 16 | Breaking changes, zero benefit for this project |
| SQLAlchemy/ORM | Overkill for 7 simple tables with raw SQL |
| Redux/MobX | Zustand is lighter, simpler, better for real-time |
| WebSockets | SSE is sufficient for one-way push |
| ECharts | 300KB+ for one treemap; Nivo is lighter |
| Prisma | Wrong ecosystem (TypeScript ORM for Node, not Python) |
| Socket.io | Overkill; EventSource handles SSE natively |

---

## Roadmap Implications

1. **Database layer first** — Portfolio APIs, trade execution, and LLM chat all depend on the database. asyncpg pool + schema init should be Phase 1.
2. **LLM integration needs care** — The LiteLLM + OpenRouter structured output bug means building the `extra_body` approach first, with direct httpx fallback ready.
3. **Frontend can start after APIs exist** — Next.js 15 scaffold + Tailwind v4 theme + SSE hook can be built in parallel with backend API work, but full integration requires working endpoints.
4. **E2E tests last** — Require both frontend and backend running in Docker Compose.

---

## Open Questions

- LiteLLM's OpenRouter structured output bug may be fixed in a future release (issue #13438). Check before implementation.
- @nivo/treemap v0.99.x compatibility with React 19 needs validation during frontend scaffolding.
- Vitest vs Jest for Next.js 15: evaluate effort vs benefit during frontend setup.

---

*Stack analysis: 2026-03-01*
