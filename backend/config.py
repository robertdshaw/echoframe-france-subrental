"""
EchoFrame France Subrental Intelligence — runtime configuration.

Reads from environment variables (Pydantic settings). Sensible defaults
let the dashboard run end-to-end with seed data alone — no API keys
required for the demo.
"""

from __future__ import annotations

import json
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All runtime configuration in one place."""

    # ---------------------------------------------------------------
    # Identity
    # ---------------------------------------------------------------
    app_name: str = "EchoFrame France Subrental Intelligence"
    app_version: str = "0.1.0"
    environment: str = Field("development", description="development / production")

    # ---------------------------------------------------------------
    # API
    # ---------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
        ]
    )

    # ---------------------------------------------------------------
    # Database
    # ---------------------------------------------------------------
    database_url: str = Field(
        "sqlite:///./echoframe_france.db",
        description="SQLAlchemy URL. SQLite for MVP; postgres-ready.",
    )

    # ---------------------------------------------------------------
    # External services (all optional — graceful fallback to seeds)
    # ---------------------------------------------------------------
    anthropic_api_key: Optional[str] = None
    newsdata_api_key: Optional[str] = None
    insee_api_key: Optional[str] = None
    bdf_api_key: Optional[str] = None

    # LLM model identifiers
    narrative_model: str = "claude-sonnet-4-6"
    haiku_model: str = "claude-haiku-4-5-20251001"

    # ---------------------------------------------------------------
    # Cost gate
    # ---------------------------------------------------------------
    llm_cost_ceiling_eur: float = Field(
        50.0,
        description="Hard monthly ceiling on Anthropic spend; fails closed.",
    )

    # ---------------------------------------------------------------
    # Feature flags
    # ---------------------------------------------------------------
    enable_live_apis: bool = True
    enable_nlp: bool = True
    enable_regime_detection: bool = True

    # ---------------------------------------------------------------
    # Cache
    # ---------------------------------------------------------------
    forecast_cache_ttl_minutes: int = 60
    narrative_cache_ttl_minutes: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        """Accept JSON-string env var (Render style) or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

    def get_cors_settings(self) -> dict:
        """Settings for fastapi.middleware.cors.CORSMiddleware.

        IMPORTANT: allow_credentials cannot be True when origins is a
        wildcard. The Argentina build learned this the hard way — browsers
        silently reject the preflight, surfacing as the bare 'Network
        Error' axios message. We derive the flag from the origin list.
        """
        wildcard = any(o == "*" for o in self.cors_origins)
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": not wildcard,
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["*"],
        }

    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
