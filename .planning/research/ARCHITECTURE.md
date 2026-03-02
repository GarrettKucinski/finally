# Architecture Research: AI Trading Workstation

> Research dimension: Architecture
> Project: FinAlly -- AI Trading Workstation
> Context: Brownfield -- market data layer complete (strategy pattern, PriceCache, SSE streaming). Researching architecture for remaining components: database, portfolio, trade execution, LLM chat, frontend, Docker.
> Date: 2026-03-01

---

## Executive Summary

The existing market data layer provides clean integration points via `PriceCache.get_price()`, `get_all()`, `add_ticker()`, and `remove_ticker()` — no modifications needed. The remaining system follows a **layered service architecture**: routes delegate to service functions, services contain business logic, database access via raw asyncpg with connection pooling. FastAPI lifespan is the single orchestration point. The build order is driven by dependency chains: Database → Portfolio/Watchlist → LLM Chat → Frontend → Polish → Docker/E2E.

---

## Component Architecture

### Existing Components (No Changes Needed)

```
┌─────────────────────────────────────────────┐
│ Market Data Layer (COMPLETE)                 │
│                                              │
│  MarketDataSource (ABC)                      │
│    ├── SimulatorDataSource (GBM)             │
│    └── MassiveDataSource (REST polling)      │
│                                              │
│  PriceCache (thread-safe in-memory)          │
│    ├── get_price(ticker) → PriceUpdate       │
│    ├── get_all() → dict[str, PriceUpdate]    │
│    └── update(ticker, price)                 │
│                                              │
│  SSE Stream Router (/api/stream/prices)      │
│  Factory (env-gated source selection)        │
│  Config (Pydantic Settings)                  │
└─────────────────────────────────────────────┘
```

### New Components

```
┌─────────────────────────────────────────────┐
│ Database Layer                               │
│                                              │
│  db.py - Pool creation, schema init          │
│    ├── create_pool(dsn) → asyncpg.Pool       │
│    ├── init_schema(pool) → CREATE IF NOT     │
│    └── seed_defaults(pool) → INSERT IF EMPTY │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Service Layer                                │
│                                              │
│  portfolio_service.py                        │
│    ├── get_portfolio(pool, user_id)          │
│    ├── execute_trade(pool, cache, user_id,   │
│    │                 ticker, qty, side)       │
│    ├── get_trade_history(pool, user_id)      │
│    └── record_snapshot(pool, cache, user_id) │
│                                              │
│  watchlist_service.py                        │
│    ├── get_watchlist(pool, cache, user_id)   │
│    ├── add_ticker(pool, source, user_id, t)  │
│    └── remove_ticker(pool, source, user_id,t)│
│                                              │
│  chat_service.py                             │
│    ├── process_message(pool, cache, source,  │
│    │                   user_id, message)      │
│    ├── build_context(pool, cache, user_id)   │
│    ├── call_llm(messages) → ChatResponse     │
│    └── execute_actions(pool, cache, source,  │
│                        user_id, response)     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ API Route Layer                              │
│                                              │
│  routes/portfolio.py                         │
│    ├── GET  /api/portfolio                   │
│    ├── POST /api/portfolio/trade             │
│    └── GET  /api/portfolio/history           │
│                                              │
│  routes/watchlist.py                         │
│    ├── GET    /api/watchlist                 │
│    ├── POST   /api/watchlist                 │
│    └── DELETE /api/watchlist/{ticker}        │
│                                              │
│  routes/chat.py                              │
│    └── POST /api/chat                        │
│                                              │
│  routes/health.py                            │
│    └── GET  /api/health                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Background Tasks                             │
│                                              │
│  Portfolio snapshot recorder (every 30s)     │
│  Snapshot cleanup (delete > 24h old)         │
│  (Market data source — already exists)       │
└─────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Price Streaming Flow (Existing)

```
MarketDataSource ──update──▶ PriceCache ──read──▶ SSE Generator ──push──▶ EventSource (browser)
     (500ms)                  (in-memory)           (500ms)              (onmessage callback)
```

### Trade Execution Flow (New)

```
User clicks Buy/Sell
       │
       ▼
POST /api/portfolio/trade {ticker, qty, side}
       │
       ▼
portfolio_service.execute_trade()
       │
       ├── 1. PriceCache.get_price(ticker) → fill price
       ├── 2. BEGIN TRANSACTION
       ├── 3. SELECT cash, position FOR UPDATE (lock row)
       ├── 4. Validate (enough cash/shares?)
       ├── 5. UPDATE positions (upsert or delete if qty=0)
       ├── 6. UPDATE users_profile (cash balance)
       ├── 7. INSERT INTO trades (history log)
       ├── 8. COMMIT
       └── 9. Record portfolio snapshot (async, post-trade)
       │
       ▼
Return {portfolio state, trade confirmation}
```

### LLM Chat Flow (New)

```
User sends message
       │
       ▼
POST /api/chat {message}
       │
       ▼
chat_service.process_message()
       │
       ├── 1. Save user message to chat_messages
       ├── 2. Build context:
       │      ├── System prompt (role, instructions)
       │      ├── Portfolio snapshot (positions, cash, P&L)
       │      ├── Watchlist with live prices
       │      └── Last 20 chat messages
       ├── 3. Call LLM via LiteLLM → OpenRouter (Cerebras)
       │      └── Structured output: {message, trades[], watchlist_changes[]}
       ├── 4. Parse response (with retry + fallback)
       ├── 5. Auto-execute actions:
       │      ├── For each trade → portfolio_service.execute_trade()
       │      └── For each watchlist change → watchlist_service.add/remove
       │      └── Collect per-action results (success/failure)
       ├── 6. Save assistant message + actions to chat_messages
       └── 7. Return {message, executed_actions}
```

### Frontend Data Flow (New)

```
┌─────────────────────────────────────────────────────────┐
│ Browser                                                  │
│                                                          │
│  EventSource(/api/stream/prices)                         │
│       │                                                  │
│       ▼                                                  │
│  Zustand Price Store ─────────────────────┐              │
│       │              │          │          │              │
│       ▼              ▼          ▼          ▼              │
│  Watchlist     Main Chart   Portfolio   Header           │
│  (sparklines)  (LW Charts)  Heatmap    (total value)    │
│                                                          │
│  Trade Bar ──POST /api/portfolio/trade──▶ Backend        │
│  Chat Panel ──POST /api/chat──▶ Backend                  │
│                                                          │
│  On trade/chat response → refetch portfolio state        │
└─────────────────────────────────────────────────────────┘
```

---

## Integration Patterns

### Dependency Injection via FastAPI Lifespan + app.state

The FastAPI lifespan is the single orchestration point:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create database pool
    pool = await create_pool(settings.database_url)
    await init_schema(pool)
    await seed_defaults(pool)

    # 2. Create price cache and market data source (existing)
    cache = PriceCache()
    source = create_market_data_source(settings, cache)

    # 3. Load watchlist tickers from DB → start market source
    tickers = await get_watchlist_tickers(pool, DEFAULT_USER_ID)
    await source.start(tickers)

    # 4. Start background tasks
    snapshot_task = asyncio.create_task(snapshot_loop(pool, cache))
    cleanup_task = asyncio.create_task(cleanup_loop(pool))

    # 5. Wire dependencies onto app.state
    app.state.pool = pool
    app.state.cache = cache
    app.state.source = source

    # 6. Include routers
    app.include_router(create_stream_router(cache))  # existing
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)
    app.include_router(health_router)

    try:
        yield
    finally:
        snapshot_task.cancel()
        cleanup_task.cancel()
        await source.stop()
        await pool.close()
```

Route handlers access shared state via `request.app.state`:

```python
@router.get("/api/portfolio")
async def get_portfolio(request: Request):
    pool = request.app.state.pool
    cache = request.app.state.cache
    return await portfolio_service.get_portfolio(pool, cache, DEFAULT_USER_ID)
```

### Service Layer Pattern

Services are plain async functions (not classes). They receive their dependencies as arguments:

```python
# portfolio_service.py
async def execute_trade(
    pool: asyncpg.Pool,
    cache: PriceCache,
    user_id: str,
    ticker: str,
    quantity: float,
    side: str,
) -> TradeResult:
    price = cache.get_price(ticker)
    if price is None:
        raise ValueError(f"No price available for {ticker}")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # ... trade logic
```

This keeps services testable (pass mock pool/cache) without framework coupling.

### Watchlist ↔ Market Source Synchronization

The watchlist service must update BOTH the database AND the live market source:

```python
async def add_ticker(pool, source, user_id, ticker):
    await db_add_watchlist(pool, user_id, ticker)  # persist
    await source.add_ticker(ticker)                 # start streaming
```

This ensures the SSE stream includes newly added tickers immediately.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Tempting | What to Do Instead |
|-------------|-------------------|-------------------|
| ORM for 7 tables | "Best practice" | Raw asyncpg — simpler, faster, no migration framework |
| Separate DB connection per request | "Isolation" | Connection pool — Neon charges per connection |
| React Context for prices | "No extra dependency" | Zustand — Context re-renders all consumers on any change |
| Chart component re-creation per tick | "Fresh data" | `series.update()` — append data, don't recreate chart |
| LLM streaming (token-by-token) | "Better UX" | Complete response — structured output can't be parsed incrementally |
| Separate trade path for LLM | "Different validation" | Same `execute_trade()` function — consistency, single validation path |

---

## Risk Assessment

| Component | Risk | Reason |
|-----------|------|--------|
| Database layer | LOW | Standard asyncpg + Neon pattern, well-documented |
| Portfolio/Trade execution | LOW | Straightforward CRUD with transaction |
| Watchlist CRUD | LOW | Simple add/remove with market source sync |
| LLM structured output | MEDIUM | Known LiteLLM + OpenRouter bug; `extra_body` workaround needed |
| Chat auto-execution | MEDIUM | Must handle partial failures (some trades succeed, others fail) |
| SSE → Frontend | LOW | EventSource is browser-native; existing backend proven |
| Real-time UI performance | MEDIUM | 500ms updates × 10 tickers requires careful state management |
| Docker orchestration | LOW | Standard two-service compose with healthcheck |

---

## Suggested Build Order

Based on dependency chains:

### Phase 1: Database Foundation
- asyncpg pool creation in lifespan
- Schema init (CREATE TABLE IF NOT EXISTS)
- Seed default user + watchlist
- Health check endpoint (includes DB ping)

### Phase 2: Portfolio & Watchlist APIs
- Portfolio service (positions, cash, P&L calculation)
- Trade execution (with transaction, validation)
- Watchlist CRUD (with market source sync)
- Portfolio snapshots (background task)
- All REST endpoints for these services

### Phase 3: LLM Chat Integration
- System prompt construction
- Portfolio context builder
- LiteLLM call with structured output (extra_body workaround)
- Response parsing with retry + fallback
- Auto-execution pipeline
- Chat message persistence
- Mock mode for testing

### Phase 4: Frontend Foundation
- Next.js 15 scaffold + Tailwind v4 dark theme
- SSE hook (usePriceStream) with Zustand store
- Watchlist panel with live prices + flash animations
- Trade bar (buy/sell)
- Portfolio table
- Header (total value, connection status, cash)

### Phase 5: Frontend Polish & Visualizations
- Sparkline mini-charts in watchlist
- Main detail chart (Lightweight Charts)
- Portfolio heatmap (Nivo treemap)
- P&L chart (portfolio value over time)
- AI chat panel (messages, loading, inline actions)

### Phase 6: Docker & E2E
- Dockerfiles (frontend + backend)
- docker-compose.yml with healthcheck
- docker-compose.test.yml with Playwright
- E2E test scenarios
- .env.example

---

*Architecture analysis: 2026-03-01*
