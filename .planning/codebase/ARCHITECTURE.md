# Architecture

**Analysis Date:** 2026-03-01

## Pattern Overview

**Overall:** Strategy pattern with pluggable market data sources, communicating through a shared thread-safe cache.

**Key Characteristics:**
- **Source abstraction**: Two market data implementations (simulator and Massive REST API) behind a single abstract interface
- **Cache-driven**: All downstream code reads from a shared `PriceCache` rather than directly from the data source
- **Thread-safe**: Lock-protected cache handles both async market sources and blocking REST client calls via `asyncio.to_thread()`
- **Version-based change detection**: SSE streaming uses monotonic version counter to avoid redundant serialization
- **Decoupled layers**: Market data layer is completely independent from (future) portfolio, chat, and database layers

## Layers

**Market Data Source Layer:**
- Purpose: Produce price updates on a schedule (polling or simulation)
- Location: `backend/app/market/simulator.py`, `backend/app/market/massive_client.py`
- Contains: `SimulatorDataSource` (GBM-based), `MassiveDataSource` (REST polling)
- Depends on: `PriceCache` (writes), `MarketDataSource` interface (implements)
- Used by: FastAPI app startup/shutdown (lifecycle), watchlist operations (add/remove tickers)

**Cache Layer:**
- Purpose: Thread-safe in-memory store for latest price of each ticker
- Location: `backend/app/market/cache.py`
- Contains: `PriceCache` class with read/write operations
- Depends on: `PriceUpdate` model, `threading.Lock`
- Used by: SSE streaming endpoint, portfolio valuation (future), trade execution (future)

**Models Layer:**
- Purpose: Define immutable data contracts
- Location: `backend/app/market/models.py`
- Contains: `PriceUpdate` frozen dataclass with computed properties (change, direction)
- Depends on: None (pure data)
- Used by: `PriceCache`, SSE streaming, all consumers

**Interface Layer:**
- Purpose: Define the contract all market data sources must implement
- Location: `backend/app/market/interface.py`
- Contains: `MarketDataSource` ABC with `start()`, `stop()`, `add_ticker()`, `remove_ticker()`, `get_tickers()`
- Depends on: None
- Used by: Both simulator and Massive implementations, factory

**Factory Layer:**
- Purpose: Select the appropriate market data source at startup based on environment
- Location: `backend/app/market/factory.py`
- Contains: `create_market_data_source()` function
- Depends on: `MASSIVE_API_KEY` env var, both data source implementations
- Used by: FastAPI app initialization

**Streaming Layer:**
- Purpose: Push price updates to connected clients via Server-Sent Events
- Location: `backend/app/market/stream.py`
- Contains: `create_stream_router()` factory that returns a FastAPI router with `/api/stream/prices` endpoint
- Depends on: `PriceCache` (reads), FastAPI
- Used by: FastAPI app (include_router during startup)

**Configuration Layer:**
- Purpose: Provide seed prices, GBM parameters, and correlation matrices
- Location: `backend/app/market/seed_prices.py`
- Contains: `SEED_PRICES` dict, `TICKER_PARAMS` dict, correlation constants, `CORRELATION_GROUPS`
- Depends on: None (configuration data)
- Used by: `GBMSimulator` during initialization

## Data Flow

**Price Update Flow (Real-time):**

1. Market data source (simulator or Massive) generates a price update
2. Source writes to `PriceCache.update(ticker, price)`
3. `PriceCache` creates a `PriceUpdate` object with computed direction/change
4. `PriceUpdate` is stored in cache and version counter increments
5. SSE streaming generator detects version change
6. Generator serializes all prices via `PriceUpdate.to_dict()` to JSON
7. JSON payload sent to all connected clients as `data: {...}\n\n`
8. Browser client receives EventSource message, parses JSON, updates UI

**Watchlist Change Flow:**

1. User adds/removes ticker from watchlist (via API endpoint, not yet implemented)
2. Endpoint calls `market_source.add_ticker()` or `market_source.remove_ticker()`
3. For add: source adds ticker to active set, next poll/simulation step includes it
4. For remove: source removes from active set, `PriceCache.remove()` called to clean cache
5. SSE continues streaming, now with new/fewer tickers

**Initialization Flow:**

1. FastAPI app startup event runs
2. `create_market_data_source()` reads `MASSIVE_API_KEY` env var
3. If set → returns `MassiveDataSource`, else → returns `SimulatorDataSource`
4. App calls `await source.start(initial_watchlist_tickers)`
5. Source initializes background task (polling loop or GBM step loop)
6. App creates SSE router via `create_stream_router(price_cache)`
7. App includes router in FastAPI app
8. App is now ready to accept SSE connections and serve prices

**Shutdown Flow:**

1. FastAPI app shutdown event runs
2. App calls `await market_source.stop()`
3. Source cancels background task and cleans up (closes REST client, etc.)
4. SSE connections gracefully disconnect (CancelledError caught)

## Key Abstractions

**MarketDataSource (Interface):**
- Purpose: Contract that both simulator and Massive implementations must fulfill
- Examples: `SimulatorDataSource`, `MassiveDataSource` in `backend/app/market/simulator.py`, `backend/app/market/massive_client.py`
- Pattern: Abstract base class with async lifecycle methods and ticker management

**PriceCache:**
- Purpose: Single source of truth for current prices; decouples producers from consumers
- Examples: Instantiated in `backend/app/market/cache.py`, injected into sources and routers
- Pattern: Thread-safe wrapper around dict with version counter

**PriceUpdate:**
- Purpose: Immutable snapshot of a single ticker's price with computed derived fields
- Examples: Created by `PriceCache.update()`, serialized by `PriceUpdate.to_dict()`
- Pattern: Frozen dataclass with `@property` computed fields (change, direction, change_percent)

**Factory Pattern:**
- Purpose: Defer selection of concrete market data source until runtime
- Examples: `create_market_data_source()` returns either `SimulatorDataSource` or `MassiveDataSource`
- Pattern: Function-based factory reading environment variables

## Entry Points

**FastAPI App Startup:**
- Location: (To be implemented in `backend/main.py`, not yet created)
- Triggers: Container startup or `uvicorn backend:app`
- Responsibilities: Create market source, start it, create and include SSE router

**Market Data Source Initialization:**
- Location: `backend/app/market/factory.py::create_market_data_source()`
- Triggers: Called during app startup
- Responsibilities: Read `MASSIVE_API_KEY`, instantiate and return appropriate source

**SSE Endpoint:**
- Location: `backend/app/market/stream.py::stream_prices()`
- Triggers: Browser `new EventSource('/api/stream/prices')`
- Responsibilities: Stream price updates via SSE, handle client disconnect, version-based change detection

**GBM Simulator Step Loop:**
- Location: `backend/app/market/simulator.py::SimulatorDataSource._step_loop()`
- Triggers: Called during `source.start()`
- Responsibilities: Run GBM math, update cache, maintain correlated price paths

**Massive API Polling Loop:**
- Location: `backend/app/market/massive_client.py::MassiveDataSource._poll_loop()`
- Triggers: Called during `source.start()`
- Responsibilities: Poll Massive snapshot endpoint every N seconds, update cache

## Error Handling

**Strategy:** Logging with graceful degradation; downstream code doesn't crash on data source failures.

**Patterns:**
- **Source startup failure**: If `source.start()` fails, app startup fails (fail fast)
- **Source polling/simulation failure**: Logged, next cycle retries (no state corruption due to immutable `PriceUpdate`)
- **SSE client disconnect**: Caught as `asyncio.CancelledError`, loop exits cleanly
- **Cache thread contention**: Lock-protected; threads wait, no data loss
- **Version counter overflow**: Monotonic increment in Python int, no practical limit

## Cross-Cutting Concerns

**Logging:**
- `logging.getLogger(__name__)` in each module
- Used to track source selection, startup/shutdown, polling errors, tick counts
- No logging in hot paths (per-tick logging disabled to avoid spam)

**Thread Safety:**
- `threading.Lock` in `PriceCache` protects all mutations
- Required because Massive REST client runs in thread pool via `asyncio.to_thread()`
- All mutations use `with self._lock:` guard
- Public methods (`update()`, `get()`, `get_all()`, `version`) are thread-safe

**Testing:**
- Market data layer is fully tested in `backend/tests/market/`
- Tests cover GBM math, Massive response parsing, cache thread safety, SSE change detection
- Conftest provides shared test fixtures

---

*Architecture analysis: 2026-03-01*
