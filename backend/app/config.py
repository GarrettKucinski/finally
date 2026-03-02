"""
Application configuration via Pydantic Settings.

Loads environment variables (and optionally a .env file) into a typed,
validated Settings instance. Fails fast with a clear error if required
variables (DATABASE_URL) are missing.

Usage:
    settings = get_settings()  # cached singleton
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings loaded from environment variables.

    Required:
        database_url: Neon Postgres connection string

    Optional (with defaults):
        openrouter_api_key: OpenRouter API key for LLM (default: "", tightened in Phase 3)
        massive_api_key: Massive/Polygon.io API key for real market data (default: "")
        llm_mock: If True, return deterministic mock LLM responses (default: False)
    """

    database_url: str
    openrouter_api_key: str = ""
    massive_api_key: str = ""
    llm_mock: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Create and cache a Settings instance.

    Not instantiated at module level to avoid breaking tests that need
    to control environment variables before Settings is created.
    """
    return Settings()
