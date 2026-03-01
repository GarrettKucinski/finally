"""
Market data package for FinAlly.

Public API — downstream code imports only from app.market:

    from app.market import PriceCache, create_market_data_source

All other modules are internal implementation details.
"""

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
