"""
Tests for app.market.factory — create_market_data_source().

7 tests covering:
- MASSIVE_API_KEY set → returns MassiveDataSource
- MASSIVE_API_KEY empty → returns SimulatorDataSource
- MASSIVE_API_KEY absent → returns SimulatorDataSource
- Whitespace-only key treated as empty
"""

import os

import pytest

from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource


@pytest.fixture
def cache() -> PriceCache:
    return PriceCache()


class TestFactorySourceSelection:
    """create_market_data_source() selects the right implementation."""

    def test_no_api_key_returns_simulator(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_empty_api_key_returns_simulator(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "")
        source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_whitespace_api_key_returns_simulator(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        """A whitespace-only key is treated as absent."""
        monkeypatch.setenv("MASSIVE_API_KEY", "   ")
        source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)

    def test_valid_api_key_returns_massive(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "test-api-key-123")
        source = create_market_data_source(cache)
        assert isinstance(source, MassiveDataSource)

    def test_massive_source_gets_api_key(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "my-real-key")
        source = create_market_data_source(cache)
        assert isinstance(source, MassiveDataSource)
        assert source._api_key == "my-real-key"

    def test_massive_source_gets_cache(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
        source = create_market_data_source(cache)
        assert isinstance(source, MassiveDataSource)
        assert source._cache is cache

    def test_simulator_source_gets_cache(self, cache: PriceCache, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        source = create_market_data_source(cache)
        assert isinstance(source, SimulatorDataSource)
        assert source._cache is cache
