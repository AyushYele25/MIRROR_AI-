"""Application configuration via Pydantic Settings.

All config is loaded from environment variables (or .env file).
"""

from __future__ import annotations

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, typed configuration for the MIRROR AI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://localhost:5432/mirror_ai"

    # ── GitHub ───────────────────────────────────────────────────
    github_token: str = ""

    # ── Gemini LLM ───────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = '["http://localhost:3000"]'

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse the JSON-encoded CORS origins string."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_analyze_per_hour: int = 10
    rate_limit_api_per_minute: int = 60

    # ── Analysis Limits ──────────────────────────────────────────
    max_repos_per_user: int = 20
    max_commits_per_repo: int = 500
    max_files_per_repo: int = 200
    max_file_size_bytes: int = 524_288  # 512 KB

    # ── Caching ──────────────────────────────────────────────────
    github_cache_ttl_hours: int = 24

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


# Singleton — import this everywhere
settings = Settings()
