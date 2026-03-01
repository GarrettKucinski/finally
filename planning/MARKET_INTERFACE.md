# Market Data Interface Design

Unified Python API for retrieving stock prices in FinAlly. The backend uses one of two implementations — selected automatically by configuration — behind a common interface.

---

## Design Principle

All downstream code (SSE streaming, trade execution, portfolio valuation) is agnostic to the data source. A factory function inspects the `MASSIVE_API_KEY` setting and returns the appropriate provider. Both implementations write to a shared in-memory price cache.

```
┌──────────────────────┐     ┌──────────────────────┐
│   MarketSimulator    │     │    MassiveProvider    │
│   (GBM, in-process)  │     │  (REST polling)       │
└─────────┬────────────┘     └─────────┬────────────┘
          │ implements                  │ implements
          ▼                            ▼
   ┌──────────────────────────────────────┐
   │     MarketDataProvider (ABC)         │
   │  start() / stop()                   │
   │  get_price(ticker) → PriceData      │
   │  get_all_prices() → dict            │
   │  add_ticker() / remove_ticker()     │
   └──────────────────┬───────────────────┘
                      │ writes to
                      ▼
            ┌──────────────────┐
            │   Price Cache    │
            │  dict[str, PriceData]
            └────────┬─────────┘
                     │ read by
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       SSE stream  Trade fill  Portfolio P&L
```

---

## Data Structures

### PriceData

The canonical price object used throughout the backend.

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PriceData:
    """Immutable snapshot of a ticker's current price state."""

    ticker: str
    price: float
    previous_price: float
    timestamp: datetime
    change: float         # price - previous_price
    change_pct: float     # percentage change
    direction: str        # "up" | "down" | "flat"
```

**Why frozen dataclass?**
- `frozen=True` prevents SSE readers from accidentally mutating shared state
- `slots=True` reduces memory (no `__dict__` per instance)
- Lightweight — created at high frequency (~2/sec per ticker), no Pydantic overhead

### TickerConfig

Per-ticker configuration for the simulator. The Massive provider doesn't need this.

```python
@dataclass(frozen=True, slots=True)
class TickerConfig:
    """Per-ticker simulation parameters."""

    ticker: str
    seed_price: float
    mu: float       # annualized drift
    sigma: float    # annualized volatility
    sector: str
```

---

## Abstract Interface

```python
from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """Interface that both the simulator and Massive client implement.

    Downstream code depends only on this interface. The factory
    function selects the concrete implementation at startup.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start background data generation or polling."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down the provider."""
        ...

    @abstractmethod
    def get_price(self, ticker: str) -> PriceData | None:
        """Get the latest price for a single ticker."""
        ...

    @abstractmethod
    def get_all_prices(self) -> dict[str, PriceData]:
        """Get latest prices for all tracked tickers."""
        ...

    @abstractmethod
    def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the tracked set."""
        ...

    @abstractmethod
    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the tracked set."""
        ...

    @property
    @abstractmethod
    def poll_interval(self) -> float:
        """Seconds between price updates (used by SSE cadence)."""
        ...
```

**Why `abc.ABC` over `typing.Protocol`?**
- Explicit contract — subclassing makes the relationship clear
- Fails at instantiation time if a method is missing, not at call time
- Allows shared non-abstract methods later (e.g., a `_log_update` helper)

---

## Factory Function

```python
from backend.config import Settings


def create_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Select the market data implementation based on configuration.

    - If MASSIVE_API_KEY is set and non-empty → MassiveProvider (REST polling)
    - Otherwise → MarketSimulator (GBM simulation)
    """
    if settings.massive_api_key:
        from backend.market.massive import MassiveProvider
        return MassiveProvider(
            api_key=settings.massive_api_key,
            poll_interval=15.0,  # safe for the free tier
        )

    from backend.market.simulator import MarketSimulator
    return MarketSimulator()
```

Called once during FastAPI lifespan startup. The returned instance is stored on `app.state`.

---

## FastAPI Integration

### Lifespan (startup/shutdown)

```python
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()

    # Initialize database
    await init_database(settings.database_url)

    # Create and start market data provider
    provider = create_market_data_provider(settings)
    await provider.start()

    # Start portfolio snapshot background task
    snapshot_task = asyncio.create_task(
        portfolio_snapshot_loop(provider, settings.database_url),
        name="portfolio-snapshot-loop",
    )

    # Store on app.state for route handlers
    app.state.provider = provider
    app.state.settings = settings

    yield

    # Shutdown
    snapshot_task.cancel()
    await asyncio.gather(snapshot_task, return_exceptions=True)
    await provider.stop()


app = FastAPI(lifespan=lifespan)
```

### SSE Streaming Endpoint

```python
import json
from fastapi import Request
from sse_starlette.sse import EventSourceResponse


@app.get("/api/stream/prices")
async def stream_prices(request: Request):
    provider: MarketDataProvider = request.app.state.provider

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            prices = provider.get_all_prices()
            data = {
                ticker: {
                    "ticker": pd.ticker,
                    "price": pd.price,
                    "previousPrice": pd.previous_price,
                    "change": pd.change,
                    "changePct": pd.change_pct,
                    "direction": pd.direction,
                    "timestamp": pd.timestamp.isoformat(),
                }
                for ticker, pd in prices.items()
            }

            yield {"event": "prices", "data": json.dumps(data)}
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())
```

### Trade Execution (Price Lookup)

```python
@app.post("/api/portfolio/trade")
async def execute_trade(trade: TradeRequest, request: Request):
    provider: MarketDataProvider = request.app.state.provider

    # Get fill price from the live cache
    price_data = provider.get_price(trade.ticker)
    if price_data is None:
        raise HTTPException(400, detail=f"No price available for {trade.ticker}")

    fill_price = price_data.price
    # ... execute trade at fill_price ...
```

---

## Implementation Summaries

### MarketSimulator

- Generates prices using Geometric Brownian Motion (GBM) with per-ticker drift and volatility
- Correlated moves via Cholesky-decomposed sector correlation matrix
- Occasional random jumps (0.1% chance per tick, 2-5% move)
- Updates every 500ms as an asyncio background task
- Seed prices for ~50 popular tickers; unknown tickers default to $100

Full design: [MARKET_SIMULATOR.md](MARKET_SIMULATOR.md)

### MassiveProvider

- Polls `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=...` on a configurable interval
- Single API call returns data for all watchlist tickers
- Uses `httpx.AsyncClient` with connection pooling, Bearer auth, exponential backoff on 429/5xx
- Parses response via Pydantic `PolygonSnapshotResponse` model, converts to `PriceData`
- Free tier: 15s poll interval. Paid tiers: 2-5s.

Full API reference: [MASSIVE_API.md](MASSIVE_API.md)

---

## Thread Safety

All access happens on the asyncio event loop (single thread). The price cache is a `dict[str, PriceData]`. This is safe because:

1. Coroutines only switch at `await` points — no concurrent mutation
2. `dict[key] = value` is atomic in CPython (GIL)
3. `PriceData` is frozen — readers can't mutate it after the write

No locks are needed. If thread-pool executors ever access the cache, add `asyncio.Lock`.

---

## File Organization

```
backend/
├── market/
│   ├── __init__.py          # re-exports MarketDataProvider, PriceData, factory
│   ├── interface.py         # MarketDataProvider ABC + PriceData + TickerConfig
│   ├── simulator.py         # MarketSimulator class
│   ├── massive.py           # MassiveProvider class
│   ├── seed_data.py         # DEFAULT_TICKER_CONFIGS dict (~50 tickers)
│   └── correlations.py      # SECTOR_CORRELATIONS dict + build_correlation_matrix()
```

---

## Required Packages

| Package | Purpose |
|---------|---------|
| `httpx` | Async HTTP client for Massive API polling |
| `numpy` | Vectorized GBM math, Cholesky decomposition |
| `pydantic` | Massive API response parsing, API schemas |
| `pydantic-settings` | Config validation (`Settings` class) |
| `sse-starlette` | SSE response for FastAPI |
