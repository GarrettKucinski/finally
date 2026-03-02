# External Integrations

**Analysis Date:** 2026-03-01

## APIs & External Services

**Market Data (Polygon.io via Massive):**
- Massive API (Polygon.io) - Real-time stock market data
  - SDK/Client: `massive` 1.0.0+
  - Auth: `MASSIVE_API_KEY` environment variable
  - Optional: If not set, backend uses built-in GBM simulator
  - Endpoint: `GET snapshot_all()` for market type STOCKS
  - Implementation: `backend/app/market/massive_client.py`
  - Rate limiting: Free tier 5 req/min → polls every 15 seconds

**LLM Integration:**
- OpenRouter (serving Cerebras inference)
  - SDK/Client: LiteLLM (referenced in PLAN.md, implementation pending)
  - Model: `openrouter/openai/gpt-oss-120b` via Cerebras
  - Auth: `OPENROUTER_API_KEY` environment variable
  - Structured outputs enabled for response parsing
  - Used for: Chat messages, portfolio analysis, auto-executing trades
  - Mock mode available: `LLM_MOCK=true` for testing

## Data Storage

**Database:**
- Neon serverless PostgreSQL
  - Connection: `DATABASE_URL` environment variable (e.g., `postgresql://user:pass@...?sslmode=require`)
  - Client: asyncpg 0.29.0+ (async Python driver)
  - Connection pooling: Handled by Neon's serverless proxy
  - Initialization: On startup via FastAPI lifespan event — creates tables if missing, seeds default data
  - Schema includes: `users`, `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`

**In-Memory Cache:**
- Price cache (no external storage)
  - Type: In-process dictionary with threading.Lock
  - Scope: Current server instance only
  - Populated by: MarketDataSource (Simulator or Massive)
  - Consumed by: SSE streaming, portfolio valuation, trade execution

**File Storage:**
- Local filesystem only (no external object storage)
- Schema SQL files: `backend/schema/` (created by schema initialization tasks)

**Caching:**
- None (beyond PriceCache)

## Authentication & Identity

**Auth Provider:**
- Custom (stubbed for future use)
- Current implementation: Single hardcoded default user
  - User ID: Fixed UUID
  - Email: `default@finally.app`
  - Password: Placeholder (hashed, not used for v1)
- Schema includes `users` table with email/password columns for future login
- All tables FK to `users(id)` via `user_id` UUID field

**Multi-User Readiness:**
- Database schema designed for multi-user support
- All tables have `user_id` FK to `users(id)`
- No changes needed to migrate from default user to per-request auth

## Monitoring & Observability

**Error Tracking:**
- None (logs to stdout via Python logging module)

**Logs:**
- Python standard logging module
- Configured per module (e.g., `logger = logging.getLogger(__name__)`)
- Output to console for Docker
- Error logs on Massive API failures, malformed snapshot responses, market data polling errors

**Structured Logging:**
- Not currently used; plain text log messages

## CI/CD & Deployment

**Hosting:**
- Docker (containerized, two services via docker-compose)
- Deployment targets: AWS App Runner, Render, or any container platform
- No Docker volumes for state (Neon Postgres as persistent storage)

**CI Pipeline:**
- Not yet configured (future GitHub Actions)

**Local Development:**
- `docker compose up` - Builds and runs both frontend and backend
- `docker compose down` - Stops and removes containers

**Environment Management:**
- `.env` file (gitignored)
- `.env.example` committed as template
- Required vars checked at startup (Pydantic Settings validation)

## Environment Configuration

**Required env vars:**
```
DATABASE_URL=postgresql://...
OPENROUTER_API_KEY=...
```

**Optional env vars:**
```
MASSIVE_API_KEY=        (if not set, uses simulator)
LLM_MOCK=false          (set true for deterministic E2E tests)
BACKEND_URL=...         (set by docker-compose for frontend rewrites)
```

**Secrets location:**
- `.env` file (local development, gitignored)
- Container: Passed via `env_file: .env` in docker-compose.yml
- Production: Environment variables in container orchestration platform (App Runner, Render, etc.)

## Webhooks & Callbacks

**Incoming:**
- None (frontend and backend are request-response only)

**Outgoing:**
- None currently

## Background Tasks

**Market Data Polling:**
- Simulator: Async loop updating PriceCache at ~500ms intervals
  - Uses geometric Brownian motion with sector-based correlation
  - Runs in-process as asyncio task
  - Location: `backend/app/market/simulator.py`

- Massive: Async loop polling REST API at fixed intervals (15s for free tier)
  - Executes synchronous REST calls via `asyncio.to_thread()`
  - Thread-safe via PriceCache locks
  - Location: `backend/app/market/massive_client.py`

**Portfolio Snapshots:**
- Background task (implementation pending) to record portfolio value every 30 seconds
- Also records immediately after trade execution
- Cleanup task deletes snapshots older than 24 hours
- Storage: `portfolio_snapshots` table in Postgres

**LLM Chat:**
- On-demand (no background processing)
- Triggered by user message via POST `/api/chat`
- Auto-executes trades and watchlist changes specified by LLM response
- All actions logged to `chat_messages` table with JSONB action details

## Rate Limiting & Quotas

**Massive API (Polygon.io):**
- Free tier: 5 requests/minute → poll interval set to 15 seconds
- Paid tiers: Configurable poll intervals (2-15 seconds)
- Strategy: Single API call per poll cycle fetches all watched tickers

**OpenRouter (LLM):**
- Per Cerebras tier (not rate-limited for typical usage)
- No caching of responses

## Data Flow

**Price Updates:**
1. MarketDataSource (Simulator or Massive) generates/fetches prices
2. Prices written to PriceCache via `update()` method
3. Version counter incremented
4. SSE generator detects version change, serializes all prices, sends to clients
5. Frontend receives JSON, updates price display, triggers flash animation

**Trade Execution:**
1. User sends POST `/api/portfolio/trade` with ticker, quantity, side
2. Backend looks up current price from PriceCache
3. Validates: sufficient cash (buy) or shares (sell)
4. Updates `positions` table (or deletes if quantity → 0)
5. Records entry in `trades` (append-only log)
6. Immediately records portfolio snapshot to `portfolio_snapshots`
7. Returns updated portfolio state to frontend

**Chat Interaction:**
1. User sends message via POST `/api/chat`
2. Backend loads portfolio context, last 20 messages from `chat_messages`
3. Constructs LLM prompt with system message + context + history + user message
4. Calls OpenRouter/Cerebras via LiteLLM
5. Parses structured JSON response (message, trades[], watchlist_changes[])
6. Auto-executes trades and watchlist changes with validation
7. Stores message + action details in `chat_messages` (JSONB actions)
8. Returns complete response (message + action results) to frontend

---

*Integration audit: 2026-03-01*
