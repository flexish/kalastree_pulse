"""
Centralized application configuration.

All environment-dependent values live here and nowhere else. Every other
module reads settings through `get_settings()` instead of touching
`os.environ` directly — this keeps configuration testable (settings can be
overridden in tests) and gives us one place to extend when later phases
introduce Google Sheets credentials, AI provider keys, Supabase/Postgres
DSNs, and JWT secrets.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels above this file (app/core/config.py -> app -> root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings, sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application identity -------------------------------------------------
    APP_NAME: str = "Kalastree Pulse"
    APP_TAGLINE: str = "Every day, the team reflects. The company learns. The tree grows."
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Server -----------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Security (wired up starting Phase 2 - Authentication) -----------------
    SECRET_KEY: str = "change-me-in-production"
    SESSION_COOKIE_NAME: str = "kalastree_session"

    # --- Admin (Phase 7) --------------------------------------------------------
    # A single shared password, not a per-user credential — there's still no user
    # table. This is layered on top of the regular name-based session rather than
    # a second login system: you must already be signed in, then this unlocks an
    # `is_admin` flag in that same session. Real role-based access is explicitly
    # future-ready work (see README), not this phase's job.
    ADMIN_PASSWORD: str = "change-me-admin"

    # --- Team ---------------------------------------------------------------
    # There's no user roster by default, so participation % is measured
    # against this configurable headcount rather than a real membership list.
    TEAM_SIZE: int = 10

    # Off by default — any correctly-formatted name can sign in (Phase 2's
    # original behavior), so the app never accidentally locks everyone out
    # before config/team_roster.json has been populated. Turn on once it's
    # filled in — see config/README.md.
    TEAM_ROSTER_ENABLED: bool = False

    # --- Logging ------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # --- Filesystem paths (derived, not meant to be overridden via env) --------
    BASE_DIR: Path = BASE_DIR
    APP_DIR: Path = BASE_DIR / "app"
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    LOG_DIR: Path = BASE_DIR / "logs"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (env is read once per process)."""
    return Settings()
