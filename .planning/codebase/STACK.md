# Technology Stack

**Analysis Date:** 2026-03-01

## Languages

**Primary:**
- Python 3.12+ - Backend (FastAPI)
- TypeScript - Frontend (Next.js) — placeholder, not yet implemented

**Secondary:**
- SQL - Database schema and queries (Postgres)

## Runtime

**Environment:**
- Python 3.12 (backend requirement: `requires-python = ">=3.12"`)
- Node.js 20 (frontend, via Docker slim image)

**Package Manager:**
- uv - Python package manager (modern, fast, reproducible)
- Lockfile: `backend/uv.lock` (present, 164KB)

## Frameworks

**Core Backend:**
- FastAPI 0.115.0+ - REST API framework, async-first with type validation
- Uvicorn 0.32.0+ - ASGI application server
- Pydantic 2.8.0+ - Data validation and settings management
- Pydantic Settings 2.3.0+ - Environment variable management and startup validation

**Database:**
- asyncpg 0.29.0+ - Async Postgres driver (thread-safe connection pooling)

**Streaming:**
- sse-starlette 2.1.0+ - Server-Sent Events (SSE) support for real-time price streaming

**Frontend (Planned):**
- Next.js (TypeScript) - Full-stack React framework with SSR
- Tailwind CSS - Utility-first CSS framework

## Key Dependencies

**Critical:**
- fastapi 0.115.0+ - Web framework, handles routing, request validation
- uvicorn[standard] 0.32.0+ - ASGI server runtime
- asyncpg 0.29.0+ - Database connectivity, connection pooling via Neon proxy

**Market Data:**
- massive 1.0.0+ - REST client for Polygon.io market data (optional, environment-gated)
- numpy 2.0.0+ - Numerical computing for geometric Brownian motion simulator

**HTTP:**
- httpx 0.27.0+ - Async HTTP client library

**Utilities:**
- rich 13.0.0+ - Terminal output formatting and pretty printing

## Configuration

**Environment:**
- Environment variables loaded via Pydantic Settings from `.env` file
- Critical vars: `DATABASE_URL` (Postgres), `OPENROUTER_API_KEY` (LLM), `MASSIVE_API_KEY` (optional market data)
- Optional vars: `LLM_MOCK` (testing mode)

**Build:**
- `backend/pyproject.toml` - uv project manifest, hatchling build backend

## Testing Framework

**Backend:**
- pytest 8.3.0+ - Test runner with asyncio support
- pytest-asyncio 0.24.0+ - Async test fixtures
- pytest-cov 5.0.0+ - Coverage reporting

**Code Quality:**
- ruff 0.7.0+ - Fast Python linter (enforces E, F, I, UP rule sets, 100-char line length)

## Platform Requirements

**Development:**
- Python 3.12+ (or uv manages via `.python-version`)
- Docker & Docker Compose (for containerized development)

**Production:**
- Neon serverless Postgres database (managed, no self-hosted DB required)
- Docker/container runtime (ECR, App Runner, Render, etc.)
- OPENROUTER_API_KEY for LLM integration (Cerebras inference via LiteLLM)

## Architecture Notes

**Backend Structure:**
- `backend/app/market/` - Market data layer (abstraction, simulator, Massive integration)
- `backend/app/market/interface.py` - Abstract `MarketDataSource` base class
- `backend/app/market/simulator.py` - GBM simulator with correlated price generation
- `backend/app/market/massive_client.py` - Massive REST API client (Polygon.io)
- `backend/app/market/cache.py` - Thread-safe in-memory price cache
- `backend/app/market/stream.py` - FastAPI SSE router for `/api/stream/prices`
- `backend/app/market/factory.py` - Environment-gated selection (Massive vs Simulator)

**Thread Safety:**
- PriceCache uses `threading.Lock` to protect in-memory state
- Massive client's synchronous REST calls run via `asyncio.to_thread()` in a thread pool
- Simulator runs asynchronously in event loop (no blocking)

**Async Model:**
- FastAPI app is fully async
- SSE generator yields events to `StreamingResponse`
- Background tasks (simulator polling or Massive REST polling) update shared PriceCache

---

*Stack analysis: 2026-03-01*
