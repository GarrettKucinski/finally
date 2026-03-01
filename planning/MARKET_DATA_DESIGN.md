# Market Data Backend — Detailed Design

Implementation-ready design for the FinAlly market data subsystem. Covers the data model, thread-safe price cache, abstract interface, GBM simulator, Massive (Polygon.io) API client, environment-driven factory, SSE streaming endpoint, and FastAPI lifecycle integration.

Everything lives under `backend/app/market/`.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Structure](#2-file-structure)
3. [Data Model — `models.py`](#3-data-model)
4. [Price Cache — `cache.py`](#4-price-cache)
5. [Abstract Interface — `interface.py`](#5-abstract-interface)
6. [Seed Prices & Ticker Parameters — `seed_prices.py`](#6-seed-prices--ticker-parameters)
7. [GBM Simulator — `simulator.py`](#7-gbm-simulator)
8. [Massive API Client — `massive_client.py`](#8-massive-api-client)
9. [Factory — `factory.py`](#9-factory)
10. [SSE Streaming Endpoint — `stream.py`](#10-sse-streaming-endpoint)
11. [Package Exports — `__init__.py`](#11-package-exports)
12. [FastAPI Lifecycle Integration](#12-fastapi-lifecycle-integration)
13. [Watchlist Coordination](#13-watchlist-coordination)
14. [Testing Strategy](#14-testing-strategy)
15. [Error Handling & Edge Cases](#15-error-handling--edge-cases)
16. [Configuration Summary](#16-configuration-summary)

---

## 1. Architecture Overview

Two data source implementations (simulator and Massive API) share a single abstract interface. Downstream code — SSE streaming, portfolio valuation, trade execution — is completely source-agnostic. The environment variable `MASSIVE_API_KEY` selects which implementation runs.

```
                          ┌─────────────────────┐
                          │ MASSIVE_API_KEY set? │
                          └─────────┬───────────┘
                        yes ┌───────┴───────┐ no
                            ▼               ▼
                   MassiveDataSource  SimulatorDataSource
                   (REST polling)     (GBM simulation)
                            │               │
                            │  implements   │
                            ▼               ▼
                     MarketDataSource (ABC)
                            │
                            │  writes to
                            ▼
                  ┌────────────────────┐
                  │  PriceCache        │
                  │  (thread-safe,     │
                  │   in-memory)       │
                  └──────┬─────────────┘
                         │ reads from
              ┌──────────┼──────────────┐
              ▼          ▼              ▼
         SSE stream   Portfolio      Trade
         endpoint     valuation    execution
         (/api/       (GET /api/   (POST /api/
          stream/      portfolio)   portfolio/
          prices)                   trade)
```

### Design Principles

- **Strategy pattern** — both sources implement `MarketDataSource`; the factory picks one
- **PriceCache as single point of truth** — producers write, consumers read, no coupling
- **Push model** — sources push to the cache on their own schedule; no one pulls from a source
- **Immutable data** — `PriceUpdate` is a frozen dataclass; safe to share across readers
- **Thread safety** — cache uses `threading.Lock` because the Massive client runs sync API calls via `asyncio.to_thread`

---

## 2. File Structure

```
backend/
  app/
    market/
      __init__.py           # Public API re-exports
      models.py             # PriceUpdate frozen dataclass
      cache.py              # PriceCache (thread-safe in-memory store)
      interface.py          # MarketDataSource ABC
      seed_prices.py        # SEED_PRICES, TICKER_PARAMS, correlation groups
      simulator.py          # GBMSimulator + SimulatorDataSource
      massive_client.py     # MassiveDataSource (Polygon.io REST poller)
      factory.py            # create_market_data_source()
      stream.py             # SSE endpoint router factory
  tests/
    market/
      __init__.py
      test_models.py        # 11 tests — PriceUpdate fields, properties, edge cases
      test_cache.py         # 13 tests — thread safety, version counter, CRUD
      test_simulator.py     # 17 tests — GBM math, correlation, random events
      test_simulator_source.py  # 10 tests — async lifecycle, cache integration
      test_factory.py       # 7 tests  — env-based source selection
      test_massive.py       # 13 tests — REST polling, snapshot parsing, errors
```

**~500 lines** of production code across 8 modules, covered by **73 tests**.

---

## 3. Data Model

**File:** `backend/app/market/models.py`

A single immutable dataclass is the only data type that leaves the market data layer. All consumers work with `PriceUpdate` objects.

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round(
            (self.price - self.previous_price) / self.previous_price * 100, 4
        )

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

### Design Notes

| Decision | Rationale |
|---|---|
| `frozen=True` | Immutable — safe to share across async tasks and threads without copying |
| `slots=True` | Lower memory footprint, faster attribute access (CPython optimization) |
| Computed properties | `change`, `change_percent`, `direction` are derived from price/previous_price — computed on read, not stored, to guarantee consistency |
| `timestamp` default | `field(default_factory=time.time)` auto-stamps when the `PriceUpdate` is created if no explicit timestamp is provided |
| `to_dict()` | Returns a plain dict for `json.dumps()` in the SSE stream — avoids coupling to any serialization framework |

### Example

```python
update = PriceUpdate(ticker="AAPL", price=191.50, previous_price=190.00)
print(update.direction)       # "up"
print(update.change)          # 1.5
print(update.change_percent)  # 0.7895
print(update.to_dict())
# {"ticker": "AAPL", "price": 191.5, "previous_price": 190.0,
#  "timestamp": 1709312400.0, "change": 1.5, "change_percent": 0.7895,
#  "direction": "up"}
```

---

## 4. Price Cache

**File:** `backend/app/market/cache.py`

The central data store. One writer (the active data source) pushes prices in; multiple readers (SSE endpoint, portfolio, trade execution) pull prices out.

```python
from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(self, ticker: str, price: float,
               timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous price.
        If this is the first update for the ticker, previous_price == price
        (direction='flat').
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

### Key Design Details

**Version counter for SSE change detection.** Every `update()` call increments `self._version`. The SSE generator compares its `last_version` to `cache.version` each cycle — if unchanged, it skips the payload. This avoids serializing and sending identical data when no prices have moved (important for the Massive poller, which only updates every 15 seconds).

**Thread safety with `threading.Lock`.** Although most operations are within a single asyncio event loop, the Massive client runs synchronous REST calls via `asyncio.to_thread()`, which executes in a thread pool. The lock guarantees safe concurrent access between the polling thread and the async SSE reader.

**First update bootstrapping.** When a ticker appears for the first time, `previous_price` is set equal to `price`, producing `direction="flat"` and `change=0`. This avoids nonsensical huge percentage changes on the first tick.

**Memory bounded at O(tickers).** The cache stores only the latest `PriceUpdate` per ticker — no history accumulation.

### Usage by Downstream Code

```python
cache = PriceCache()

# Trade execution reads current price
price = cache.get_price("AAPL")  # float or None

# Portfolio valuation reads all prices
all_prices = cache.get_all()  # dict[str, PriceUpdate]
for ticker, update in all_prices.items():
    current_value = update.price * position_quantity

# SSE checks for changes before sending
if cache.version != last_version:
    data = {t: u.to_dict() for t, u in cache.get_all().items()}
    yield f"data: {json.dumps(data)}\n\n"
```

---

## 5. Abstract Interface

**File:** `backend/app/market/interface.py`

The contract that both data sources implement. Downstream code depends only on this interface, never on a concrete implementation.

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must be called exactly once. Calling start() twice is undefined behavior.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not write
        to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. No-op if not present.

        Also removes the ticker from the PriceCache.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

### Method Contract Summary

| Method | Async | Idempotent | Notes |
|---|---|---|---|
| `start(tickers)` | Yes | No — call exactly once | Launches a background `asyncio.Task` |
| `stop()` | Yes | Yes — safe to call multiple times | Cancels background task, cleans up |
| `add_ticker(ticker)` | Yes | Yes — no-op if already present | Takes effect on the next cycle |
| `remove_ticker(ticker)` | Yes | Yes — no-op if not present | Also clears the cache entry |
| `get_tickers()` | No | Yes | Returns a copy; safe to call anytime |

---

## 6. Seed Prices & Ticker Parameters

**File:** `backend/app/market/seed_prices.py`

Constants used by the simulator: realistic starting prices, per-ticker volatility/drift parameters, and sector-based correlation groups.

```python
# Realistic starting prices for the default watchlist
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},   # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},   # High volatility, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},   # Low volatility (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},   # Low volatility (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for tickers not in the list above (dynamically added)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6      # Tech stocks move together
INTRA_FINANCE_CORR = 0.5   # Finance stocks move together
CROSS_GROUP_CORR = 0.3     # Between sectors / unknown tickers
TSLA_CORR = 0.3            # TSLA does its own thing
```

### Volatility Spectrum

The `sigma` values are tuned to reflect real-world behavior at the simulation's 500ms tick rate:

| Volatility | Tickers | Sigma | Character |
|---|---|---|---|
| Low | V, JPM | 0.17–0.18 | Steady, small moves — payment/bank stocks |
| Moderate | MSFT, AAPL, GOOGL | 0.20–0.25 | Balanced — large-cap tech staples |
| High | AMZN, META, NFLX | 0.28–0.35 | More movement — growth/media stocks |
| Very high | NVDA, TSLA | 0.40–0.50 | Wild — GPU/EV momentum plays |

### Correlation Matrix

The full 10×10 correlation matrix looks like:

```
         AAPL  GOOGL  MSFT  AMZN  TSLA  NVDA  META   JPM    V   NFLX
AAPL     1.0   0.6   0.6   0.6   0.3   0.6   0.6   0.3   0.3   0.6
GOOGL    0.6   1.0   0.6   0.6   0.3   0.6   0.6   0.3   0.3   0.6
MSFT     0.6   0.6   1.0   0.6   0.3   0.6   0.6   0.3   0.3   0.6
AMZN     0.6   0.6   0.6   1.0   0.3   0.6   0.6   0.3   0.3   0.6
TSLA     0.3   0.3   0.3   0.3   1.0   0.3   0.3   0.3   0.3   0.3
NVDA     0.6   0.6   0.6   0.6   0.3   1.0   0.6   0.3   0.3   0.6
META     0.6   0.6   0.6   0.6   0.3   0.6   1.0   0.3   0.3   0.6
JPM      0.3   0.3   0.3   0.3   0.3   0.3   0.3   1.0   0.5   0.3
V        0.3   0.3   0.3   0.3   0.3   0.3   0.3   0.5   1.0   0.3
NFLX     0.6   0.6   0.6   0.6   0.3   0.6   0.6   0.3   0.3   1.0
```

TSLA is in the tech group but treated independently (0.3 correlation with everything). This is a deliberate modeling choice — TSLA's price moves are often driven by Elon Musk tweets and sentiment rather than sector fundamentals.

### Dynamically Added Tickers

When a user adds a ticker not in `SEED_PRICES` (e.g., "PYPL"):
- **Starting price:** random between $50–$300
- **GBM params:** `DEFAULT_PARAMS` (sigma=0.25, mu=0.05)
- **Correlation:** 0.3 with all existing tickers (falls through to `CROSS_GROUP_CORR`)
- **Cholesky matrix:** rebuilt to include the new ticker

---

## 7. GBM Simulator

**File:** `backend/app/market/simulator.py`

Two classes: `GBMSimulator` (the math engine) and `SimulatorDataSource` (the async wrapper that implements `MarketDataSource`).

### 7.1 GBMSimulator — The Math Engine

Generates correlated stock price paths using Geometric Brownian Motion with Cholesky-decomposed correlations and random shock events.

```python
import math
import random
import numpy as np

class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    Math:
        S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)

    Where:
        S(t)   = current price
        mu     = annualized drift (expected return)
        sigma  = annualized volatility
        dt     = time step as fraction of a trading year
        Z      = correlated standard normal random variable
    """

    # 500ms expressed as a fraction of a trading year
    # 252 trading days * 6.5 hours/day * 3600 seconds/hour = 5,896,800 seconds
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability

        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        # Generate n independent standard normal draws
        z_independent = np.random.standard_normal(n)

        # Apply Cholesky to get correlated draws
        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            # GBM step
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random event: ~0.1% chance per tick per ticker
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker. Rebuilds the correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker. Rebuilds the correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)
```

#### GBM Math Explained

At each 500ms tick, each price evolves as:

```
S(t+dt) = S(t) × exp((μ − σ²/2) × dt + σ × √dt × Z)
```

The `dt` is tiny (~8.48×10⁻⁸) because 500ms is a minuscule fraction of a 252-day trading year. This produces sub-cent moves per tick that accumulate naturally — TSLA at σ=0.50 generates roughly the right intraday range over a simulated trading day.

Key mathematical properties:
- **Prices can never go negative** — `exp()` is always positive
- **Lognormal distribution** — matches real market returns
- **Drift term** `(μ − σ²/2)` — Itô's correction ensures the expected return is actually `μ`
- **Sub-cent moves** — at dt≈8.5e-8, even TSLA (σ=0.50) moves ~$0.003 per tick

#### Cholesky Decomposition for Correlated Moves

To make stocks in the same sector move together:

1. Build the n×n correlation matrix `C` from the sector-based rules
2. Compute the lower-triangular Cholesky factor `L = cholesky(C)`
3. Each step: generate n independent standard normals `Z_ind`, then `Z_corr = L × Z_ind`

```python
def _rebuild_cholesky(self) -> None:
    n = len(self._tickers)
    if n <= 1:
        self._cholesky = None
        return

    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
            corr[i, j] = rho
            corr[j, i] = rho

    self._cholesky = np.linalg.cholesky(corr)

@staticmethod
def _pairwise_correlation(t1: str, t2: str) -> float:
    tech = CORRELATION_GROUPS["tech"]
    finance = CORRELATION_GROUPS["finance"]

    if t1 == "TSLA" or t2 == "TSLA":
        return TSLA_CORR           # 0.3

    if t1 in tech and t2 in tech:
        return INTRA_TECH_CORR     # 0.6
    if t1 in finance and t2 in finance:
        return INTRA_FINANCE_CORR  # 0.5

    return CROSS_GROUP_CORR        # 0.3
```

Rebuild cost is O(n²), but n is small (< 50 tickers in practice). The matrix is rebuilt only when tickers are added/removed, not on every tick.

#### Random Shock Events

Every step, each ticker has a 0.1% chance of a sudden 2–5% move:

```python
if random.random() < 0.001:
    shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
    self._prices[ticker] *= (1 + shock)
```

With 10 tickers ticking at 2 Hz, expect a shock event somewhere roughly every 50 seconds — frequent enough to be visually interesting, rare enough to feel like real market drama.

### 7.2 SimulatorDataSource — Async Wrapper

Wraps `GBMSimulator` in a `MarketDataSource` that runs as an asyncio background task.

```python
class SimulatorDataSource(MarketDataSource):

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(
            tickers=tickers,
            event_probability=self._event_prob,
        )
        # Seed the cache with initial prices so SSE has data immediately
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

#### Lifecycle Detail

1. **`start(tickers)`** — Creates the `GBMSimulator` with all tickers, seeds the cache with initial prices (so the first SSE client gets data immediately, no delay), then launches the background task.
2. **`_run_loop()`** — Calls `step()` every 500ms, writes each new price to the cache. Catches and logs exceptions but never crashes — the loop always continues.
3. **`add_ticker(ticker)`** — Adds to the simulator (triggers Cholesky rebuild), then seeds the cache immediately so the new ticker has a price before the next tick.
4. **`remove_ticker(ticker)`** — Removes from both the simulator and the cache.
5. **`stop()`** — Cancels the background task and awaits its completion. Safe to call multiple times.

---

## 8. Massive API Client

**File:** `backend/app/market/massive_client.py`

REST-polling data source backed by the Massive (Polygon.io) API. Fetches snapshots for all watched tickers in a single API call and writes results to the PriceCache.

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)
        # Immediate first poll so cache has data right away
        await self._poll_once()
        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)
```

### Polling Loop

```python
async def _poll_loop(self) -> None:
    """Poll on interval. First poll already happened in start()."""
    while True:
        await asyncio.sleep(self._interval)
        await self._poll_once()

async def _poll_once(self) -> None:
    """Execute one poll cycle: fetch snapshots, update cache."""
    if not self._tickers or not self._client:
        return

    try:
        # The Massive RESTClient is synchronous — run in a thread
        # to avoid blocking the event loop.
        snapshots = await asyncio.to_thread(self._fetch_snapshots)
        for snap in snapshots:
            try:
                price = snap.last_trade.price
                # Massive timestamps are Unix milliseconds → convert to seconds
                timestamp = snap.last_trade.timestamp / 1000.0
                self._cache.update(
                    ticker=snap.ticker,
                    price=price,
                    timestamp=timestamp,
                )
            except (AttributeError, TypeError) as e:
                logger.warning("Skipping snapshot for %s: %s",
                               getattr(snap, "ticker", "???"), e)
    except Exception as e:
        logger.error("Massive poll failed: %s", e)
        # Don't re-raise — the loop will retry on the next interval.

def _fetch_snapshots(self) -> list:
    """Synchronous call to the Massive REST API. Runs in a thread."""
    return self._client.get_snapshot_all(
        market_type=SnapshotMarketType.STOCKS,
        tickers=self._tickers,
    )
```

### API Details

**Endpoint used:** `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,...`

This returns all tickers in a **single API call** — critical for staying within free-tier rate limits (5 req/min).

**Fields extracted per snapshot:**

| Field | Source | Notes |
|---|---|---|
| `price` | `snap.last_trade.price` | Most recent trade price (float) |
| `timestamp` | `snap.last_trade.timestamp / 1000` | Unix ms → seconds |
| `ticker` | `snap.ticker` | Uppercase ticker symbol |

**Error handling:** API failures (`401`, `429`, `5xx`, network errors) are caught and logged. The loop sleeps and retries on the next interval — it never crashes.

### Rate Limiting

| Tier | Limit | Recommended Poll Interval |
|---|---|---|
| Free | 5 req/min | 15 seconds (default) |
| Paid (Starter) | Higher | 5 seconds |
| Paid (Developer+) | Unlimited | 2 seconds |

The `poll_interval` parameter controls how often the poller hits the API. The default (15s) is safe for free-tier keys.

### Thread Safety

`_fetch_snapshots()` is a synchronous blocking call to the Massive REST client. It runs via `asyncio.to_thread()` to avoid blocking the event loop. This is why `PriceCache` uses a `threading.Lock` — the cache write from the polling thread and the cache read from the SSE coroutine can happen concurrently.

---

## 9. Factory

**File:** `backend/app/market/factory.py`

Selects the appropriate `MarketDataSource` implementation based on the `MASSIVE_API_KEY` environment variable.

```python
import os
from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        return SimulatorDataSource(price_cache=price_cache)
```

### Decision Flow

```
MASSIVE_API_KEY env var
    │
    ├── set and non-empty  →  MassiveDataSource(api_key=key, price_cache=cache)
    │                          Poll Polygon.io REST API every 15s
    │
    └── absent or empty    →  SimulatorDataSource(price_cache=cache)
                               GBM simulation at 500ms ticks
```

The factory returns an **unstarted** source. The caller (FastAPI lifespan) must call `await source.start(initial_tickers)`.

---

## 10. SSE Streaming Endpoint

**File:** `backend/app/market/stream.py`

Server-Sent Events endpoint that pushes price updates to connected browser clients. Uses a factory pattern to inject the `PriceCache` without global state.

```python
from collections.abc import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from .cache import PriceCache

router = APIRouter(prefix="/api/stream", tags=["streaming"])

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache."""

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events."""
    # Tell the client to retry after 1 second if the connection drops
    yield "retry: 1000\n\n"

    last_version = -1

    try:
        while True:
            if await request.is_disconnected():
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {
                        ticker: update.to_dict()
                        for ticker, update in prices.items()
                    }
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
```

### SSE Protocol Details

Each SSE event follows the [Server-Sent Events spec](https://html.spec.whatwg.org/multipage/server-sent-events.html):

```
retry: 1000\n\n                              ← Reconnect after 1s on disconnect
data: {"AAPL": {...}, "GOOGL": {...}}\n\n    ← Price payload
data: {"AAPL": {...}, "GOOGL": {...}}\n\n    ← Next update ~500ms later
...
```

**Event payload structure** (JSON):
```json
{
  "AAPL": {
    "ticker": "AAPL",
    "price": 191.50,
    "previous_price": 191.48,
    "timestamp": 1709312400.123,
    "change": 0.02,
    "change_percent": 0.0105,
    "direction": "up"
  },
  "GOOGL": {
    "ticker": "GOOGL",
    "price": 175.20,
    "previous_price": 175.25,
    "timestamp": 1709312400.123,
    "change": -0.05,
    "change_percent": -0.0285,
    "direction": "down"
  }
}
```

### Version-Based Change Detection

The generator tracks `last_version` and only serializes/sends data when `cache.version` has changed. This is particularly important for the Massive data source, which only updates every 15 seconds — the SSE loop runs at 500ms but skips 29 out of every 30 cycles when there's no new data.

### Client Connection

The frontend uses the browser's native `EventSource` API:

```javascript
const source = new EventSource('/api/stream/prices');

source.onmessage = (event) => {
    const prices = JSON.parse(event.data);
    // Update UI for each ticker
    for (const [ticker, update] of Object.entries(prices)) {
        updateWatchlistRow(ticker, update);
    }
};

source.onerror = () => {
    // EventSource auto-reconnects after the server-specified retry interval (1s)
    showReconnecting();
};
```

### Response Headers

| Header | Value | Purpose |
|---|---|---|
| `Content-Type` | `text/event-stream` | SSE content type |
| `Cache-Control` | `no-cache` | Prevent caching of stream responses |
| `Connection` | `keep-alive` | Keep the TCP connection open |
| `X-Accel-Buffering` | `no` | Prevent nginx from buffering the stream |

---

## 11. Package Exports

**File:** `backend/app/market/__init__.py`

Clean public API — downstream code imports only from `app.market`, never from submodules.

```python
from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

### Usage

```python
from app.market import PriceCache, create_market_data_source, create_stream_router

cache = PriceCache()
source = create_market_data_source(cache)
stream_router = create_stream_router(cache)
```

---

## 12. FastAPI Lifecycle Integration

The market data system integrates with FastAPI's lifespan context manager. This is how the backend application wires everything together at startup and shutdown.

```python
# backend/app/main.py (integration example)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    cache = PriceCache()
    source = create_market_data_source(cache)

    # Load initial watchlist from database
    initial_tickers = await get_watchlist_tickers()  # e.g., from SQLite
    await source.start(initial_tickers)

    # Store references for request handlers
    app.state.price_cache = cache
    app.state.market_source = source

    # Mount the SSE stream router
    stream_router = create_stream_router(cache)
    app.include_router(stream_router)

    yield  # --- App is running ---

    # --- Shutdown ---
    await source.stop()

app = FastAPI(lifespan=lifespan)
```

### Startup Sequence

```
1. Create PriceCache (empty)
2. create_market_data_source(cache)   → reads MASSIVE_API_KEY
3. Load initial watchlist from SQLite  → ["AAPL", "GOOGL", ..., "NFLX"]
4. await source.start(tickers)
   ├── Simulator: creates GBMSimulator, seeds cache, launches _run_loop
   └── Massive:   creates RESTClient, polls once immediately, launches _poll_loop
5. Mount SSE router → GET /api/stream/prices is now live
6. App accepts requests
```

### Shutdown Sequence

```
1. await source.stop()
   ├── Simulator: cancels _run_loop task, awaits completion
   └── Massive:   cancels _poll_loop task, clears client
2. Cache goes out of scope (garbage collected)
```

### How Request Handlers Access Market Data

```python
# In a route handler:
@router.get("/api/portfolio")
async def get_portfolio(request: Request):
    cache: PriceCache = request.app.state.price_cache
    current_price = cache.get_price("AAPL")  # float or None
    all_prices = cache.get_all()  # dict[str, PriceUpdate]
    ...

# In the trade execution handler:
@router.post("/api/portfolio/trade")
async def execute_trade(request: Request, trade: TradeRequest):
    cache: PriceCache = request.app.state.price_cache
    source: MarketDataSource = request.app.state.market_source

    current_price = cache.get_price(trade.ticker)
    if current_price is None:
        raise HTTPException(404, f"No price available for {trade.ticker}")
    ...
```

---

## 13. Watchlist Coordination

When the user adds/removes tickers via the watchlist API or the AI chat, the backend must coordinate between the database and the market data source.

### Adding a Ticker

```python
@router.post("/api/watchlist")
async def add_to_watchlist(request: Request, body: WatchlistAdd):
    ticker = body.ticker.upper().strip()

    # 1. Insert into database
    await db_add_watchlist(ticker)

    # 2. Start tracking in market data source
    source: MarketDataSource = request.app.state.market_source
    await source.add_ticker(ticker)
    # → Simulator: adds to GBM, seeds cache immediately
    # → Massive: appends to ticker list, picks up on next poll

    return {"ticker": ticker, "status": "added"}
```

### Removing a Ticker

```python
@router.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(request: Request, ticker: str):
    ticker = ticker.upper().strip()

    # 1. Remove from database
    await db_remove_watchlist(ticker)

    # 2. Stop tracking in market data source
    source: MarketDataSource = request.app.state.market_source
    await source.remove_ticker(ticker)
    # → Removes from source AND from PriceCache

    return {"ticker": ticker, "status": "removed"}
```

### Behavior Differences Between Sources

| Action | Simulator | Massive |
|---|---|---|
| Add ticker | Immediate — seeds cache with a price right away | Deferred — appears on next poll (up to 15s delay) |
| Remove ticker | Immediate — removed from sim + cache | Immediate — removed from list + cache |
| New ticker price | Generated from seed/random + GBM | Fetched from API on next poll |

---

## 14. Testing Strategy

### Test Coverage Summary

| Test Module | Test Count | Target Module | Coverage |
|---|---|---|---|
| `test_models.py` | 11 | `models.py` | 100% |
| `test_cache.py` | 13 | `cache.py` | 100% |
| `test_simulator.py` | 17 | `simulator.py` | 98% |
| `test_simulator_source.py` | 10 | `simulator.py` (async) | Integration |
| `test_factory.py` | 7 | `factory.py` | 100% |
| `test_massive.py` | 13 | `massive_client.py` | 56% (API mocked) |
| **Total** | **73** | | **84% overall** |

### Test Categories

**Models (11 tests):**
- Computed properties: `change`, `change_percent`, `direction`
- Edge cases: zero previous price, equal prices ("flat"), negative changes
- `to_dict()` serialization
- Frozen immutability (assigning raises `FrozenInstanceError`)

**Cache (13 tests):**
- First update: `previous_price == price`, direction is "flat"
- Subsequent updates: correct direction and change computation
- `get()`, `get_all()`, `get_price()`, `remove()`
- Version counter increments on each update
- `__len__` and `__contains__`
- Thread safety (concurrent access does not corrupt state)

**Simulator (17 tests):**
- `step()` returns prices for all tickers
- Prices are always positive (GBM guarantee)
- `add_ticker()` and `remove_ticker()` work dynamically
- Cholesky matrix rebuilds correctly
- Random events apply shocks within 2–5% range
- Pairwise correlation returns correct values for all sector combinations
- Single-ticker case (no Cholesky needed)

**Simulator Source (10 tests):**
- `start()` seeds the cache immediately
- `_run_loop()` updates cache on each tick
- `add_ticker()` seeds cache for the new ticker
- `remove_ticker()` clears both simulator and cache
- `stop()` cancels the background task cleanly
- `get_tickers()` reflects current state

**Factory (7 tests):**
- `MASSIVE_API_KEY` set → returns `MassiveDataSource`
- `MASSIVE_API_KEY` empty → returns `SimulatorDataSource`
- `MASSIVE_API_KEY` absent → returns `SimulatorDataSource`
- Whitespace-only key treated as empty

**Massive (13 tests):**
- `_poll_once()` updates cache with correct prices
- Timestamp conversion from milliseconds to seconds
- Malformed snapshots are skipped (not crash)
- API errors are caught and logged
- `add_ticker()` normalizes to uppercase
- `remove_ticker()` clears from list and cache
- `stop()` cancels task and clears client

### Running Tests

```bash
cd backend

# Run all market data tests
uv run pytest tests/market/ -v

# With coverage
uv run pytest tests/market/ -v --cov=app.market --cov-report=term-missing

# Run a specific test file
uv run pytest tests/market/test_simulator.py -v
```

---

## 15. Error Handling & Edge Cases

### Simulator Resilience

| Scenario | Behavior |
|---|---|
| `step()` raises exception | Caught in `_run_loop()`, logged, loop continues on next tick |
| Empty ticker list | `step()` returns `{}`, cache is not updated |
| Cholesky fails (bad matrix) | Shouldn't happen with valid correlations (0 < ρ < 1, positive definite) |
| `add_ticker()` while running | Safe — `GBMSimulator.add_ticker()` is synchronous, called between ticks |
| `stop()` called twice | Safe — checks `self._task.done()` before cancelling |

### Massive Resilience

| Scenario | Behavior |
|---|---|
| Invalid API key (401) | Logged, loop retries on next interval |
| Rate limited (429) | Logged, loop retries after the poll interval (15s) |
| Server error (5xx) | Logged, loop retries; Massive client has built-in 3-retry |
| Network timeout | Logged, loop retries on next interval |
| Malformed snapshot | Individual snapshot skipped, others still processed |
| Market closed | Returns last traded price (may include after-hours) |
| Empty ticker list | `_poll_once()` returns early, no API call made |

### Price Cache Edge Cases

| Scenario | Behavior |
|---|---|
| First price for a ticker | `previous_price = price`, direction = "flat", change = 0 |
| `get()` for unknown ticker | Returns `None` |
| `get_price()` for unknown ticker | Returns `None` |
| `remove()` for unknown ticker | No-op (uses `dict.pop(key, None)`) |
| Concurrent reads/writes | Thread-safe via `threading.Lock` |

### SSE Edge Cases

| Scenario | Behavior |
|---|---|
| Client disconnects | Detected via `request.is_disconnected()`, loop exits cleanly |
| No price data in cache | Skips sending (doesn't send empty `{}`) |
| No changes since last send | Skips via version comparison |
| Server restart | Client auto-reconnects after 1s (SSE `retry` directive) |

---

## 16. Configuration Summary

### Environment Variables

| Variable | Required | Default | Effect |
|---|---|---|---|
| `MASSIVE_API_KEY` | No | (empty) | If set: use real market data; if empty: use simulator |

### Internal Constants

| Constant | Value | Location | Purpose |
|---|---|---|---|
| `DEFAULT_DT` | ~8.48e-8 | `simulator.py` | GBM time step (500ms / trading year) |
| `update_interval` | 0.5s | `SimulatorDataSource` | How often the simulator ticks |
| `poll_interval` | 15.0s | `MassiveDataSource` | How often to poll the REST API |
| `event_probability` | 0.001 | `GBMSimulator` | Chance of a random shock per tick per ticker |
| `INTRA_TECH_CORR` | 0.6 | `seed_prices.py` | Correlation between tech stocks |
| `INTRA_FINANCE_CORR` | 0.5 | `seed_prices.py` | Correlation between finance stocks |
| `CROSS_GROUP_CORR` | 0.3 | `seed_prices.py` | Cross-sector / unknown ticker correlation |
| SSE `retry` | 1000ms | `stream.py` | Client reconnection delay |
| SSE poll interval | 0.5s | `stream.py` | How often SSE checks for cache changes |

### Python Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | >=0.115.0 | Web framework, SSE streaming |
| `uvicorn[standard]` | >=0.32.0 | ASGI server |
| `numpy` | >=2.0.0 | Cholesky decomposition, random normals |
| `massive` | >=1.0.0 | Polygon.io REST client |
| `rich` | >=13.0.0 | Terminal demo formatting |

### Dev Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pytest` | >=8.3.0 | Test runner |
| `pytest-asyncio` | >=0.24.0 | Async test support |
| `pytest-cov` | >=5.0.0 | Coverage reporting |
| `ruff` | >=0.7.0 | Linting and formatting |
