#!/usr/bin/env python3
"""
FinAlly Market Data Simulator — Terminal Demo
==============================================

Self-contained single-file demo that proves the GBM market data simulator
works correctly. No project imports required — all logic is inlined.

Run:  cd backend && uv run python ../market_data_demo.py
  or: pip install numpy && python3 market_data_demo.py

Features:
  - Geometric Brownian Motion with sector-correlated moves (Cholesky)
  - Random shock events (~0.1% chance of 2-5% move)
  - Live-updating terminal table with color-coded direction
  - Per-ticker sparkline price history
  - Event log for notable moves (>0.3% per tick)
  - Runs for 60 seconds or until Ctrl+C

Requirements: numpy (the only non-stdlib dependency)
"""

from __future__ import annotations

import math
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy is required. Install with: pip install numpy")
    sys.exit(1)


# ─── ANSI Colors ──────────────────────────────────────────────────────────

class C:
    """ANSI color codes for terminal output."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[32m"
    RED     = "\033[31m"
    YELLOW  = "\033[33m"
    CYAN    = "\033[36m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    WHITE   = "\033[37m"
    BG_GREEN = "\033[42m"
    BG_RED   = "\033[41m"
    CLEAR   = "\033[2J\033[H"  # Clear screen and move cursor to top-left


# ─── Seed Prices & GBM Parameters ────────────────────────────────────────

SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00, "GOOGL": 175.00, "MSFT": 420.00, "AMZN": 185.00,
    "TSLA": 250.00, "NVDA": 800.00, "META": 500.00, "JPM": 195.00,
    "V": 280.00, "NFLX": 600.00,
}

TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},
    "NVDA":  {"sigma": 0.40, "mu": 0.08},
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},
    "V":     {"sigma": 0.17, "mu": 0.04},
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

SECTOR_INTRA_CORR: dict[str, float] = {
    "tech": 0.6,
    "finance": 0.5,
}
CROSS_GROUP_CORR = 0.3
TSLA_CORR = 0.3

DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                     "NVDA", "META", "JPM", "V", "NFLX"]


# ─── PriceUpdate ──────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a ticker's price."""
    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)

    @property
    def change(self) -> float:
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"


# ─── PriceCache ───────────────────────────────────────────────────────────

class PriceCache:
    """In-memory store for the latest price of each ticker."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._version: int = 0

    def update(self, ticker: str, price: float) -> PriceUpdate:
        prev = self._prices.get(ticker)
        previous_price = prev.price if prev else price
        update = PriceUpdate(
            ticker=ticker,
            price=round(price, 2),
            previous_price=round(previous_price, 2),
        )
        self._prices[ticker] = update
        self._version += 1
        return update

    def get(self, ticker: str) -> PriceUpdate | None:
        return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        return dict(self._prices)


# ─── GBM Simulator ────────────────────────────────────────────────────────

class GBMSimulator:
    """Geometric Brownian Motion simulator with correlated sector moves."""

    TRADING_SECONDS_PER_YEAR: float = 252 * 6.5 * 3600
    DEFAULT_DT: float = 0.5 / TRADING_SECONDS_PER_YEAR

    def __init__(self, tickers: list[str], event_probability: float = 0.001) -> None:
        self._dt = self.DEFAULT_DT
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            seed_price = SEED_PRICES.get(ticker, 100.0)
            params = TICKER_PARAMS.get(ticker, {"sigma": 0.25, "mu": 0.05})
            self._tickers.append(ticker)
            self._prices[ticker] = seed_price
            self._params[ticker] = params

        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: price}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        z_independent = np.random.standard_normal(n)

        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * float(z_correlated[i])
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock event
            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= (1 + shock)

            self._prices[ticker] = max(self._prices[ticker], 0.01)
            result[ticker] = round(self._prices[ticker], 2)

        return result

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

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
        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        for sector, members in CORRELATION_GROUPS.items():
            if t1 in members and t2 in members:
                return SECTOR_INTRA_CORR.get(sector, CROSS_GROUP_CORR)
        return CROSS_GROUP_CORR


# ─── Sparkline Renderer ──────────────────────────────────────────────────

SPARK_CHARS = "▁▂▃▄▅▆▇█"

def sparkline(values: list[float], width: int = 20) -> str:
    """Render a list of floats as a sparkline string."""
    if len(values) < 2:
        return " " * width
    # Use only the most recent `width` values
    vals = values[-width:]
    lo, hi = min(vals), max(vals)
    spread = hi - lo
    if spread == 0:
        return SPARK_CHARS[3] * len(vals)
    result = ""
    for v in vals:
        idx = int((v - lo) / spread * (len(SPARK_CHARS) - 1))
        idx = max(0, min(idx, len(SPARK_CHARS) - 1))
        result += SPARK_CHARS[idx]
    return result.ljust(width)


# ─── Terminal UI ──────────────────────────────────────────────────────────

DURATION = 60  # seconds
UPDATE_INTERVAL = 0.5  # seconds

running = True

def handle_sigint(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, handle_sigint)


def format_price(price: float) -> str:
    """Right-align price with consistent width."""
    return f"${price:>10,.2f}"


def format_change(pct: float) -> str:
    """Color-coded percentage change."""
    if pct > 0:
        return f"{C.GREEN}+{pct:>6.2f}%{C.RESET}"
    elif pct < 0:
        return f"{C.RED}{pct:>7.2f}%{C.RESET}"
    return f"{C.DIM}{pct:>7.2f}%{C.RESET}"


def direction_arrow(direction: str) -> str:
    if direction == "up":
        return f"{C.GREEN}▲{C.RESET}"
    elif direction == "down":
        return f"{C.RED}▼{C.RESET}"
    return f"{C.DIM}─{C.RESET}"


def main() -> None:
    global running

    # Detect terminal width
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 100

    # Initialize
    cache = PriceCache()
    sim = GBMSimulator(DEFAULT_WATCHLIST)

    # Seed cache with initial prices
    for ticker in DEFAULT_WATCHLIST:
        price = sim.get_price(ticker)
        if price is not None:
            cache.update(ticker, price)

    # Track price history for sparklines and cumulative change from seed
    history: dict[str, list[float]] = {t: [SEED_PRICES[t]] for t in DEFAULT_WATCHLIST}
    event_log: list[str] = []
    tick_count = 0
    start_time = time.time()

    print(f"{C.CLEAR}", end="")

    while running:
        elapsed = time.time() - start_time
        remaining = max(0, DURATION - elapsed)

        if elapsed >= DURATION:
            break

        # Step the simulator
        prices = sim.step()
        tick_count += 1

        for ticker, price in prices.items():
            update = cache.update(ticker, price)
            history[ticker].append(price)

            # Log notable moves (>0.3% in a single tick)
            if abs(update.change_percent) > 0.3:
                arrow = "▲" if update.direction == "up" else "▼"
                event_log.append(
                    f"[{time.strftime('%H:%M:%S')}] {ticker} {arrow} "
                    f"{update.change_percent:+.2f}% → ${price:,.2f}"
                )
                # Keep only the last 8 events
                event_log = event_log[-8:]

        # ─── Render ──────────────────────────────────────────────────
        lines: list[str] = []

        # Header
        header_bar = "═" * min(term_width, 82)
        lines.append(f"{C.CYAN}{C.BOLD}")
        lines.append(f"  ╔{header_bar}╗")
        lines.append(f"  ║  FinAlly Market Data Simulator{' ' * max(0, min(term_width, 82) - 50)}  Tick #{tick_count:<6}  ║")
        lines.append(f"  ╚{header_bar}╝{C.RESET}")
        lines.append("")

        # Timer bar
        bar_width = 30
        filled = int(bar_width * elapsed / DURATION)
        bar = f"{'█' * filled}{'░' * (bar_width - filled)}"
        lines.append(f"  {C.DIM}Time: {bar} {remaining:.0f}s remaining{C.RESET}")
        lines.append("")

        # Table header
        lines.append(
            f"  {C.BOLD}{C.YELLOW}"
            f"{'Ticker':<8}{'Price':>12}  {'Dir':^3}  {'Tick Δ':>8}  {'From Seed':>10}  {'Sparkline (last 20 ticks)'}"
            f"{C.RESET}"
        )
        lines.append(f"  {C.DIM}{'─' * min(term_width - 4, 90)}{C.RESET}")

        # Table rows
        all_prices = cache.get_all()
        for ticker in DEFAULT_WATCHLIST:
            up = all_prices.get(ticker)
            if not up:
                continue

            seed = SEED_PRICES[ticker]
            from_seed_pct = (up.price - seed) / seed * 100

            spark = sparkline(history[ticker], width=20)
            # Color the sparkline based on overall direction from seed
            if from_seed_pct > 0:
                spark_colored = f"{C.GREEN}{spark}{C.RESET}"
            elif from_seed_pct < 0:
                spark_colored = f"{C.RED}{spark}{C.RESET}"
            else:
                spark_colored = f"{C.DIM}{spark}{C.RESET}"

            arrow = direction_arrow(up.direction)
            tick_change = format_change(up.change_percent)
            seed_change = format_change(from_seed_pct)

            lines.append(
                f"  {C.BOLD}{C.WHITE}{ticker:<8}{C.RESET}"
                f"{format_price(up.price)}  "
                f"{arrow}  "
                f"{tick_change}  "
                f"{seed_change}  "
                f"{spark_colored}"
            )

        lines.append("")

        # Event log
        lines.append(f"  {C.BOLD}{C.MAGENTA}Recent Events (>0.3% single-tick moves):{C.RESET}")
        lines.append(f"  {C.DIM}{'─' * min(term_width - 4, 55)}{C.RESET}")
        if event_log:
            for event in event_log:
                lines.append(f"  {C.DIM}{event}{C.RESET}")
        else:
            lines.append(f"  {C.DIM}(none yet — waiting for notable moves...){C.RESET}")

        lines.append("")
        lines.append(f"  {C.DIM}Press Ctrl+C to exit{C.RESET}")

        # Output
        output = "\n".join(lines)
        print(f"{C.CLEAR}{output}", end="", flush=True)

        time.sleep(UPDATE_INTERVAL)

    # ─── Final Summary ───────────────────────────────────────────────────
    print(f"\n\n{C.CYAN}{C.BOLD}  Final Summary after {tick_count} ticks:{C.RESET}\n")
    print(
        f"  {C.BOLD}{'Ticker':<8}{'Seed':>12}{'Final':>12}{'Change':>10}{'Change %':>10}{C.RESET}"
    )
    print(f"  {'─' * 52}")

    total_seed = 0.0
    total_final = 0.0
    all_prices = cache.get_all()

    for ticker in DEFAULT_WATCHLIST:
        up = all_prices.get(ticker)
        if not up:
            continue
        seed = SEED_PRICES[ticker]
        change = up.price - seed
        change_pct = (change / seed) * 100
        total_seed += seed
        total_final += up.price

        color = C.GREEN if change >= 0 else C.RED
        sign = "+" if change >= 0 else ""
        print(
            f"  {C.BOLD}{ticker:<8}{C.RESET}"
            f"${seed:>10,.2f}"
            f"  ${up.price:>8,.2f}"
            f"  {color}{sign}${abs(change):>7,.2f}{C.RESET}"
            f"  {color}{sign}{change_pct:.2f}%{C.RESET}"
        )

    net_change = total_final - total_seed
    net_pct = (net_change / total_seed) * 100
    color = C.GREEN if net_change >= 0 else C.RED
    sign = "+" if net_change >= 0 else ""
    print(f"  {'─' * 52}")
    print(
        f"  {C.BOLD}{'TOTAL':<8}{C.RESET}"
        f"${total_seed:>10,.2f}"
        f"  ${total_final:>8,.2f}"
        f"  {color}{sign}${abs(net_change):>7,.2f}{C.RESET}"
        f"  {color}{sign}{net_pct:.2f}%{C.RESET}"
    )
    print()


if __name__ == "__main__":
    main()
