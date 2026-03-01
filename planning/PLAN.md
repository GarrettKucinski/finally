# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs `docker compose up` and opens `http://localhost:3000`. No login required for v1 — a default user is pre-seeded. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Two Services, Docker Compose

```
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Frontend Container (:3000)  │    │  Backend Container (:8000)   │
│                              │    │                              │
│  Next.js (TypeScript)        │    │  FastAPI (Python/uv)         │
│  ├── Pages & components      │    │  ├── /api/*     REST         │
│  ├── Tailwind styling        │    │  ├── /api/stream/* SSE       │
│  └── Rewrites proxy:         │    │  └── Background tasks:       │
│      /api/* → backend:8000   │    │      market data polling/sim │
└──────────────────────────────┘    └──────────────┬───────────────┘
         │ user accesses :3000              │
         └──── proxies /api/* ─────────────→┘
                                            │
                                            ▼
                              ┌──────────────────────────────┐
                              │  Neon Serverless Postgres     │
                              │  Connected via DATABASE_URL   │
                              └──────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, running as a full Next.js server (not a static export). Proxies `/api/*` requests to the backend via Next.js `rewrites`
- **Backend**: FastAPI (Python), managed as a `uv` project. API-only — no static file serving
- **Database**: Neon serverless Postgres, connected via `DATABASE_URL` environment variable
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Decoupled frontend/backend | Independent development and deployment, full Next.js features (SSR, rewrites), clear separation of concerns |
| Next.js rewrites for API proxy | Frontend proxies `/api/*` to backend — no CORS needed, single user-facing port, transparent to client code |
| Neon serverless Postgres | Persistent data without Docker volumes, proper SQL types (JSONB, TIMESTAMPTZ), free tier is generous, production-ready from day one |
| docker-compose with two services | `docker compose up` starts both frontend and backend; internal networking handles service discovery |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Pydantic + Pydantic Settings | Validated config on startup (fail fast), typed API schemas, single source of truth for env vars |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project
│   └── Dockerfile            # Node-based image for the frontend
├── backend/                  # FastAPI uv project (Python)
│   ├── schema/               # SQL schema definitions and seed data
│   └── Dockerfile            # Python-based image for the backend
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── docker-compose.yml        # Primary way to run the app (both services)
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project with its own `Dockerfile`. It knows nothing about Python. It proxies `/api/*` requests to the backend via Next.js `rewrites` in `next.config.ts`. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml` and `Dockerfile`. It is API-only — no static file serving. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/schema/`** contains SQL schema definitions and seed logic. The backend initializes the database on startup via a FastAPI lifespan event — creating tables if they don't exist and seeding default data.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`docker-compose.yml`** orchestrates both services. `docker compose up` builds and starts frontend + backend. The frontend is exposed on port 3000 (user-facing), the backend on port 8000 (internal, also accessible for debugging). Services communicate via Docker's internal network.

---

## 5. Environment Variables

```bash
# Required: Neon Postgres connection string
DATABASE_URL=postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/finally?sslmode=require

# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false

# Frontend only: backend URL for Next.js rewrites proxy (set by docker-compose)
BACKEND_URL=http://backend:8000
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- All env vars are loaded and validated via Pydantic Settings on startup — missing required vars cause an immediate, clear error

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers known to the system at a regular cadence (~500ms) — in the single-user model this is equivalent to the user's watchlist
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### Neon Serverless Postgres

The backend connects to a Neon Postgres database via the `DATABASE_URL` environment variable (managed by Pydantic Settings — see below). On startup (via FastAPI lifespan event), it runs `CREATE TABLE IF NOT EXISTS` statements and seeds default data if tables are empty. This means:

- No separate migration step
- No manual database setup
- A fresh Neon database is automatically initialized on first run
- Data persists in Neon — no Docker volumes needed for state

Use `asyncpg` as the async Postgres driver. Connection pooling is handled by Neon's serverless proxy automatically.

### Configuration with Pydantic Settings

All environment variables are managed via a Pydantic Settings class:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str
    massive_api_key: str = ""
    llm_mock: bool = False

    model_config = SettingsConfigDict(env_file=".env")
```

This provides validation on startup (fail fast if `DATABASE_URL` is missing), type coercion (e.g., `LLM_MOCK=true` → `bool`), and a single source of truth for all configuration. Pydantic models are also used for API request/response schemas throughout the backend.

### Schema

All tables include a `user_id` column defaulting to `'default'`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users** — User table
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `email` VARCHAR(50) NOT NULL UNIQUE
- `password` VARCHAR(100) NOT NULL

**users_profile** — User state (cash balance)
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `cash_balance` DOUBLE PRECISION (default: `10000.0`)
- `created_at` TIMESTAMPTZ (default: `NOW()`)

**watchlist** — Tickers the user is watching
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `ticker` TEXT NOT NULL
- `added_at` TIMESTAMPTZ (default: `NOW()`)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `ticker` TEXT NOT NULL
- `quantity` DOUBLE PRECISION (fractional shares supported)
- `avg_cost` DOUBLE PRECISION
- `updated_at` TIMESTAMPTZ (default: `NOW()`)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `ticker` TEXT NOT NULL
- `side` TEXT NOT NULL (`'buy'` or `'sell'`)
- `quantity` DOUBLE PRECISION (fractional shares supported)
- `price` DOUBLE PRECISION
- `executed_at` TIMESTAMPTZ (default: `NOW()`)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution. A background cleanup task deletes rows older than 24 hours.
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `total_value` DOUBLE PRECISION
- `recorded_at` TIMESTAMPTZ (default: `NOW()`)

**chat_messages** — Conversation history with LLM
- `id` UUID PRIMARY KEY (default: `gen_random_uuid()`)
- `user_id` UUID FOREIGN KEY REFERENCES users(id)
- `role` TEXT NOT NULL (`'user'` or `'assistant'`)
- `content` TEXT NOT NULL
- `actions` JSONB (trades executed, watchlist changes made; null for user messages)
- `created_at` TIMESTAMPTZ (default: `NOW()`)

### Default Seed Data

- One user: seeded with a fixed UUID, email `default@finally.app`, placeholder password
- One user profile: linked to the default user, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### Error Response Format

All error responses use a consistent Pydantic model:

```json
{"error": "Short message", "detail": "Longer explanation"}
```

HTTP status codes: 400 (validation/bad request), 404 (not found), 500 (server error).

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the last 20 messages from the `chat_messages` table
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), change % (vs seed price), and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls use relative paths (`/api/*`) — Next.js `rewrites` in `next.config.ts` proxy these to the backend service, so no CORS configuration is needed
- Tailwind CSS for styling with a custom dark theme
- Next.js runs as a full server (not static export) — enables `rewrites`, SSR if needed, and standard Next.js development workflow

---

## 11. Docker & Deployment

### Separate Dockerfiles

**`frontend/Dockerfile`** (Node 20 slim):
- Copy `frontend/` source
- `npm install && npm run build`
- Expose port 3000
- CMD: `npm start` (runs `next start`)

**`backend/Dockerfile`** (Python 3.12 slim):
- Install uv
- Copy `backend/` source
- `uv sync` (install dependencies from lockfile)
- Expose port 8000
- CMD: `uvicorn` serving FastAPI app

### Docker Compose (Primary Run Method)

`docker-compose.yml` orchestrates both services:

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - BACKEND_URL=http://backend:8000

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
```

- Start: `docker compose up` (add `--build` to rebuild)
- Stop: `docker compose down`
- User accesses `http://localhost:3000` — the frontend proxies `/api/*` to the backend via Next.js rewrites
- Backend is also accessible at `http://localhost:8000` for direct API testing/debugging
- No Docker volumes needed — all persistent data lives in Neon Postgres
- Both containers are stateless

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up both the frontend and backend containers plus a Playwright container. This keeps browser dependencies out of the production images.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Decisions Log

All review items have been resolved. Answers are recorded here for reference.

| Item | Decision |
|---|---|
| Q1. Simulator tickers | Simulator generates prices for all watchlist tickers. Hardcoded seed prices for ~50 popular US tickers; unknown tickers seed at $100. |
| Q2. Ticker validation | Accept 1-5 uppercase alpha characters only. Trim and uppercase on input. Reject anything else with 400. |
| Q3. Zero positions | Delete the row when quantity hits 0. Future buys create a fresh row. |
| Q4. Change % baseline | Use seed price as the baseline. Label as "Change" (not "Daily change"). |
| Q5. Chat history limit | Last 20 messages sent to the LLM. |
| Q6. Massive API | Massive is the API brand name (massivecorp.com), a financial data provider built on Polygon.io. Keeping it for v1. |
| Q7. Fill price | Latest value in the in-memory price cache. No staleness check. |
| Q8. Error format | `{"error": "Short message", "detail": "Longer explanation"}` with standard HTTP codes (400/404/500). Defined as a Pydantic model. |
| S1. user_id / auth | `users` table with email/password exists in schema for future auth. No login for v1 — default user is pre-seeded. All other tables FK to `users(id)` via UUID `user_id`. |
| S2. Primary keys | UUID with `gen_random_uuid()`. |
| S3. Massive API | Keep for v1. |
| S4. Correlated moves | Keep. Implement correlation matrix for realistic sector co-movement. |
| S5. Start scripts | Removed. docker-compose only. |
| S6. Snapshot retention | Keep last 24 hours. Background task deletes older rows. |
| S7. docker-compose | Primary and only run method. |
| N1. .env.example | Create from .env file. |
| N2. Watchlist endpoint | Returns tickers with latest prices (coupled to price cache). |
| N3. Charting library | Lightweight Charts. |
| N4. Malformed LLM JSON | Retry once, then return fallback error message with no actions. |
| N5. Fractional shares | Yes, UI supports fractional input. |