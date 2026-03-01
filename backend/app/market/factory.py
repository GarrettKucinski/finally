"""
Factory function for selecting the market data source.

Reads MASSIVE_API_KEY from the environment:
- Set and non-empty → MassiveDataSource (real market data via Polygon.io)
- Absent or empty  → SimulatorDataSource (GBM simulation, no API key needed)

The returned source is unstarted. The caller must await source.start(tickers).
"""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    Selection logic:
        MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
        Otherwise                          → SimulatorDataSource (GBM simulation)

    Args:
        price_cache: The shared PriceCache the source will write into.

    Returns:
        An unstarted MarketDataSource. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("MASSIVE_API_KEY found — using MassiveDataSource (real market data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("No MASSIVE_API_KEY — using SimulatorDataSource (GBM simulation)")
        return SimulatorDataSource(price_cache=price_cache)
