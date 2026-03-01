# Market Simulator Design

Approach and code structure for simulating stock prices in FinAlly using Geometric Brownian Motion (GBM) with correlated moves and random jumps.

---

## Overview

The simulator generates realistic price streams as an in-process asyncio background task. It requires zero external dependencies beyond NumPy. When `MASSIVE_API_KEY` is not set, this is the default market data source.

**Key behaviors:**
- Updates all tracked tickers every 500ms
- Correlated moves across sectors (tech stocks move together, etc.)
- Occasional random jumps (2-5% moves) for drama
- Seed prices for ~50 popular tickers; unknown tickers default to $100
- Implements the same `MarketDataProvider` interface as the Massive client

---

## GBM Mathematics

### The Formula

```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

| Symbol | Meaning |
|--------|---------|
| `S(t)` | Current price |
| `mu` | Annualized expected return (drift) |
| `sigma` | Annualized volatility |
| `dt` | Time step as a fraction of a year |
| `Z` | Standard normal random variable |

The `mu - sigma²/2` term is the **Ito correction** — it ensures the expected growth rate is exactly `mu` despite the exponentiation.

### Time Step Calibration

For visually engaging simulation, treat each tick as 1/600th of a simulated trading day:

```python
TICKS_PER_SIMULATED_DAY = 600   # ~5 min wall-clock = 1 trading day
TRADING_DAYS_PER_YEAR = 252
DT = 1.0 / (TICKS_PER_SIMULATED_DAY * TRADING_DAYS_PER_YEAR)  # ~6.6e-6
```

This produces visible but not erratic price movements. Roughly 5 minutes of real time equals one simulated trading day.

---

## Correlated Moves (Cholesky Decomposition)

### Why

Without correlation, AAPL jumping 2% while MSFT drops 3% looks unrealistic. Stocks in the same sector should tend to move together.

### How

1. Assign each ticker to a sector
2. Build an `n × n` correlation matrix from sector-level rules
3. Compute the Cholesky factor `L` (lower triangular, `C = L @ L.T`)
4. Each tick: generate `n` independent standard normals, multiply by `L` to get correlated shocks

```python
z_independent = rng.standard_normal(n)
z_correlated = L @ z_independent  # correlated shocks
```

### Sector Correlation Matrix

|  | Tech | Finance | Health | Consumer | Energy | Industrial |
|--|------|---------|--------|----------|--------|------------|
| **Tech** | **0.75** | 0.50 | 0.30 | 0.55 | 0.20 | 0.45 |
| **Finance** | 0.50 | **0.70** | 0.35 | 0.45 | 0.40 | 0.55 |
| **Health** | 0.30 | 0.35 | **0.65** | 0.30 | 0.15 | 0.30 |
| **Consumer** | 0.55 | 0.45 | 0.30 | **0.60** | 0.25 | 0.50 |
| **Energy** | 0.20 | 0.40 | 0.15 | 0.25 | **0.75** | 0.50 |
| **Industrial** | 0.45 | 0.55 | 0.30 | 0.50 | 0.50 | **0.65** |

Bold diagonal = intra-sector correlation (same sector, different stocks).

The matrix is rebuilt only when tickers are added/removed. For `n=50`, the `O(n³)` Cholesky is trivially fast (microseconds). An eigenvalue floor ensures positive definiteness before decomposition.

---

## Random Jumps

Each tick, each ticker has a 0.1% chance of a jump event. Jump sizes are log-normally distributed:

| Parameter | Value | Effect |
|-----------|-------|--------|
| `jump_probability` | 0.001 | ~1 jump per 8 min per ticker |
| `jump_mean` | 0.0 | Symmetric (equally likely up or down) |
| `jump_std` | 0.03 | Produces 2-5% moves |

```python
jump_mask = rng.random(n) < JUMP_PROBABILITY
if jump_mask.any():
    jumps = np.exp(rng.normal(0.0, JUMP_STD, size=jump_mask.sum()))
    new_prices[jump_mask] *= jumps
```

---

## Seed Prices and Per-Ticker Configuration

### Default Watchlist (10 tickers)

| Ticker | Price | Sector | Volatility (σ) | Drift (μ) |
|--------|-------|--------|----------------|-----------|
| AAPL | $264 | tech | 0.25 | 0.08 |
| GOOGL | $312 | tech | 0.28 | 0.10 |
| MSFT | $393 | tech | 0.25 | 0.09 |
| AMZN | $210 | tech | 0.30 | 0.10 |
| TSLA | $403 | tech | 0.55 | 0.12 |
| NVDA | $177 | tech | 0.50 | 0.15 |
| META | $648 | tech | 0.35 | 0.10 |
| JPM | $300 | finance | 0.22 | 0.07 |
| V | $320 | finance | 0.20 | 0.08 |
| NFLX | $96 | consumer | 0.35 | 0.10 |

### Extended Set (~40 more)

| Ticker | Price | Sector | σ | μ |
|--------|-------|--------|---|----|
| AVGO | $320 | tech | 0.35 | 0.12 |
| AMD | $200 | tech | 0.45 | 0.12 |
| CRM | $195 | tech | 0.32 | 0.09 |
| ADBE | $262 | tech | 0.30 | 0.09 |
| ORCL | $145 | tech | 0.28 | 0.08 |
| INTC | $46 | tech | 0.40 | 0.05 |
| CSCO | $79 | tech | 0.22 | 0.06 |
| PLTR | $137 | tech | 0.60 | 0.12 |
| SHOP | $121 | tech | 0.50 | 0.10 |
| SNAP | $5.20 | tech | 0.65 | 0.05 |
| UBER | $75 | tech | 0.40 | 0.10 |
| GS | $860 | finance | 0.25 | 0.08 |
| MS | $167 | finance | 0.25 | 0.07 |
| BAC | $50 | finance | 0.25 | 0.06 |
| WFC | $81 | finance | 0.24 | 0.06 |
| PYPL | $46 | finance | 0.38 | 0.08 |
| COIN | $176 | finance | 0.65 | 0.10 |
| SOFI | $18 | finance | 0.55 | 0.08 |
| JNJ | $248 | healthcare | 0.18 | 0.06 |
| PFE | $28 | healthcare | 0.28 | 0.04 |
| MRK | $124 | healthcare | 0.22 | 0.06 |
| ABBV | $232 | healthcare | 0.22 | 0.07 |
| LLY | $1052 | healthcare | 0.30 | 0.12 |
| UNH | $293 | healthcare | 0.22 | 0.08 |
| AMGN | $310 | healthcare | 0.22 | 0.06 |
| DIS | $106 | consumer | 0.30 | 0.06 |
| NKE | $62 | consumer | 0.28 | 0.06 |
| MCD | $341 | consumer | 0.18 | 0.07 |
| KO | $82 | consumer | 0.15 | 0.06 |
| PEP | $170 | consumer | 0.16 | 0.06 |
| COST | $1011 | consumer | 0.22 | 0.09 |
| WMT | $128 | consumer | 0.18 | 0.07 |
| HD | $381 | consumer | 0.22 | 0.07 |
| T | $28 | consumer | 0.20 | 0.04 |
| XOM | $153 | energy | 0.25 | 0.06 |
| CVX | $187 | energy | 0.24 | 0.06 |
| BA | $228 | industrial | 0.35 | 0.05 |
| CAT | $743 | industrial | 0.25 | 0.08 |
| DE | $630 | industrial | 0.25 | 0.07 |

**Unknown tickers** default to: `price=$100, σ=0.30, μ=0.08, sector="tech"`.

---

## Code Structure

### Class Skeleton

```python
class MarketSimulator(MarketDataProvider):
    """GBM simulator with correlated moves and jumps."""

    TICKS_PER_SIMULATED_DAY = 600
    TRADING_DAYS_PER_YEAR = 252
    DT = 1.0 / (TICKS_PER_SIMULATED_DAY * TRADING_DAYS_PER_YEAR)
    JUMP_PROBABILITY = 0.001
    JUMP_STD = 0.03
    TICK_INTERVAL = 0.5

    def __init__(self, tickers: list[str] | None = None, seed: int | None = None):
        self._rng = np.random.default_rng(seed)
        self._ticker_list: list[str] = tickers or DEFAULT_WATCHLIST
        self._configs: dict[str, TickerConfig] = ...     # from seed_data
        self._current_prices: dict[str, float] = ...     # mutable working state
        self._price_cache: dict[str, PriceData] = ...    # read by SSE/trades
        self._cholesky_L: np.ndarray = ...               # correlation factor
        self._task: asyncio.Task | None = None

    def tick(self) -> None:
        """Advance all prices by one time step (called every 500ms)."""
        # 1. Generate correlated shocks: L @ rng.standard_normal(n)
        # 2. Build vectorized mu, sigma, price arrays
        # 3. Apply GBM: prices * exp(drift + diffusion)
        # 4. Apply jumps: random 0.1% chance of 2-5% move
        # 5. Update price cache with new PriceData objects
        ...

    # MarketDataProvider interface
    def get_price(self, ticker: str) -> PriceData | None: ...
    def get_all_prices(self) -> dict[str, PriceData]: ...
    def add_ticker(self, ticker: str) -> None: ...     # rebuilds correlation
    def remove_ticker(self, ticker: str) -> None: ...  # rebuilds correlation
    async def start(self) -> None: ...                  # asyncio.create_task
    async def stop(self) -> None: ...                   # task.cancel()
    @property
    def poll_interval(self) -> float: return self.TICK_INTERVAL
```

### The tick() Method (Vectorized)

```python
def tick(self) -> None:
    n = len(self._ticker_list)
    if n == 0:
        return

    now = datetime.now(timezone.utc)
    dt = self.DT

    # Correlated random shocks
    z = self._cholesky_L @ self._rng.standard_normal(n)

    # Vectorized parameter arrays
    mu = np.array([self._configs[t].mu for t in self._ticker_list])
    sigma = np.array([self._configs[t].sigma for t in self._ticker_list])
    prices = np.array([self._current_prices[t] for t in self._ticker_list])

    # GBM step
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * z
    new_prices = prices * np.exp(drift + diffusion)

    # Random jumps
    jump_mask = self._rng.random(n) < self.JUMP_PROBABILITY
    if jump_mask.any():
        jumps = np.exp(self._rng.normal(0.0, self.JUMP_STD, size=jump_mask.sum()))
        new_prices[jump_mask] *= jumps

    # Update cache (atomic PriceData replacement per ticker)
    for i, ticker in enumerate(self._ticker_list):
        old = self._current_prices[ticker]
        new = max(float(new_prices[i]), 0.01)  # floor at $0.01
        self._current_prices[ticker] = new

        change = new - old
        self._price_cache[ticker] = PriceData(
            ticker=ticker,
            price=round(new, 2),
            previous_price=round(old, 2),
            timestamp=now,
            change=round(change, 2),
            change_pct=round(change / old * 100, 4) if old > 0 else 0.0,
            direction="up" if change > 0 else "down" if change < 0 else "flat",
        )
```

### Correlation Matrix Builder

```python
def _rebuild_correlation(self) -> None:
    """Rebuild Cholesky factor when ticker list changes."""
    n = len(self._ticker_list)
    C = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            sec_i = self._configs[self._ticker_list[i]].sector
            sec_j = self._configs[self._ticker_list[j]].sector
            corr = SECTOR_CORRELATIONS.get(
                (sec_i, sec_j),
                SECTOR_CORRELATIONS.get((sec_j, sec_i), 0.30),
            )
            C[i, j] = C[j, i] = corr

    # Eigenvalue floor → ensure positive definiteness
    eigenvalues, eigenvectors = np.linalg.eigh(C)
    eigenvalues = np.maximum(eigenvalues, 1e-8)
    C = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
    d = np.sqrt(np.diag(C))
    C = C / np.outer(d, d)

    self._cholesky_L = np.linalg.cholesky(C)
```

### Background Task Loop

```python
async def _run_loop(self) -> None:
    try:
        while True:
            self.tick()
            await asyncio.sleep(self.TICK_INTERVAL)
    except asyncio.CancelledError:
        raise  # clean shutdown

async def start(self) -> None:
    if self._task is None:
        self._task = asyncio.create_task(self._run_loop(), name="simulator")

async def stop(self) -> None:
    if self._task is not None:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
```

---

## Implementation Notes

### NumPy RNG

Use `np.random.default_rng(seed)` — the modern instance-based API. Avoids global state, is thread-safe, and supports reproducible runs when a seed is provided (useful for testing).

### Frozen Dataclasses

`PriceData` is `frozen=True, slots=True`:
- Frozen prevents SSE readers from mutating shared state
- Slots reduces per-object memory (no `__dict__`)
- Cache updates are atomic dict assignments of new `PriceData` objects

### Price Floor

`max(new_price, 0.01)` prevents display issues. GBM mathematically can't produce zero (exponential is always positive), but floating-point edge cases with extreme shocks could produce subnormal values.

### Ticker Add/Remove

When `add_ticker()` or `remove_ticker()` is called:
1. Update the ticker list and config dict
2. Rebuild the correlation matrix and Cholesky factor
3. For adds: seed the price cache with the initial price

The Cholesky rebuild is `O(n³)` but at `n=50` this is negligible.

### Performance

The entire `tick()` for 50 tickers takes single-digit microseconds (vectorized NumPy). The 500ms sleep dominates. No optimization needed.

---

## File Organization

```
backend/market/
├── interface.py         # MarketDataProvider ABC, PriceData, TickerConfig
├── simulator.py         # MarketSimulator class
├── seed_data.py         # DEFAULT_TICKER_CONFIGS, DEFAULT_WATCHLIST
└── correlations.py      # SECTOR_CORRELATIONS, build_correlation_matrix()
```

---

## Dependencies

- `numpy` — GBM math, Cholesky decomposition, vectorized operations
- Standard library only: `asyncio`, `dataclasses`, `datetime`
