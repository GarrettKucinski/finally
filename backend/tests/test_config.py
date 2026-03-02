"""
Unit tests for the Settings configuration class.

Tests verify:
- DATABASE_URL is required and validated on instantiation
- Optional fields have correct defaults
- Settings fails fast with a clear error when DATABASE_URL is missing
"""

import pytest
from pydantic import ValidationError


class TestSettings:
    """Tests for backend.app.config.Settings."""

    def test_settings_loads_database_url(self, monkeypatch):
        """Settings() with DATABASE_URL env var set creates a valid settings object."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        from app.config import Settings

        s = Settings()
        assert s.database_url == "postgresql://user:pass@host/db"

    def test_settings_fails_without_database_url(self, monkeypatch):
        """Settings() without DATABASE_URL raises ValidationError (fail-fast)."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MOCK", raising=False)
        from app.config import Settings

        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_settings_defaults(self, monkeypatch):
        """Optional fields have correct defaults: massive_api_key='', llm_mock=False, openrouter_api_key=''."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        from app.config import Settings

        s = Settings()
        assert s.massive_api_key == ""
        assert s.llm_mock is False
        assert s.openrouter_api_key == ""
