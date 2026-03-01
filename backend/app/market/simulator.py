"""
Market data simulator using Geometric Brownian Motion (GBM).

Two classes:
- GBMSimulator: the math engine (synchronous, testable in isolation)
- SimulatorDataSource: async wrapper that implements MarketDataSource

The simulator generates correlated price paths using:
    S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)

Where Z is a correlated standard normal random variable produced by
Cholesky decomposition of a sector-based correlation matrix.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    SECTOR_INTRA_CORR,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
)

logger = logging.getLogger(__name__)


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

    Correlation is achieved via Cholesky decomposition of a sector-based
    correlation matrix. Stocks in the same sector tend to move together.
    """

    # 500ms expressed as a fraction of a trading year
    # 252 trading days * 6.5 hours/day * 3600 seconds/hour = 5,896,800 seconds/year
    TRADING_SECONDS_PER_YEAR: float = 252 * 6.5 * 3600  # ~5,896,800
    DEFAULT_DT: float = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8

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
        """Advance all tickers by one time step.

        Returns a dict of {ticker: new_price}.
        Prices are always positive (guaranteed by the exponential in GBM).
        """
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

            # GBM step: S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * float(z_correlated[i])
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock event: ~0.1% chance per tick per ticker of a 2-5% move
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign

            # Floor at $0.01 to prevent display issues (GBM can't produce zero,
            # but floating-point edge cases with extreme shocks could get close)
            self._prices[ticker] = max(self._prices[ticker], 0.01)

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the simulation. Rebuilds the correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the simulation. Rebuilds the correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        """Get the current simulated price for a ticker, or None if not tracked."""
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        """Return a copy of the current ticker list."""
        return list(self._tickers)

    def _add_ticker_internal(self, ticker: str) -> None:
        """Initialize a ticker with seed price and GBM parameters."""
        seed_price = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        params = TICKER_PARAMS.get(ticker, DEFAULT_PARAMS)
        self._tickers.append(ticker)
        self._prices[ticker] = seed_price
        self._params[ticker] = params

    def _rebuild_cholesky(self) -> None:
        """Rebuild the Cholesky factor from the sector correlation matrix.

        Called whenever tickers are added or removed.
        O(n^2) matrix build + O(n^3) Cholesky — negligible at n<50.
        """
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
        """Compute the correlation between two tickers based on sector membership."""
        # TSLA does its own thing — low correlation with everything
        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR

        # Same sector → use the intra-sector correlation
        for sector, members in CORRELATION_GROUPS.items():
            if t1 in members and t2 in members:
                return SECTOR_INTRA_CORR.get(sector, CROSS_GROUP_CORR)

        # Cross-sector or unknown → baseline correlation
        return CROSS_GROUP_CORR


class SimulatorDataSource(MarketDataSource):
    """Async wrapper around GBMSimulator that implements MarketDataSource.

    Runs the simulator in a background asyncio task, writing price updates
    to a PriceCache at a configurable interval (default: 500ms).
    """

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
        """Create the simulator and launch the background update loop.

        Seeds the cache with initial prices immediately so the first SSE
        client gets data without waiting for the first tick.
        """
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
        """Cancel the background task. Safe to call multiple times."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the simulation and seed the cache immediately."""
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from both the simulation and the cache."""
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        """Return the current list of tracked tickers."""
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
                logger.exception("Simulator step failed — continuing")
            await asyncio.sleep(self._interval)
