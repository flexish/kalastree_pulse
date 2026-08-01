"""
Business KPIs.

Current values for the metrics that drive both the mission-progress card
(Phase 3) and the tree-growth rules (Phase 8) — one source of truth for
"where the business actually is right now," configurable via `KPI_*` env
vars rather than hardcoded, per the product spec. `services/mission.py`
still owns *targets* and the deadline (goal-setting is a different concern
from tracking current reality); those targets are measured against the
values here.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class KPIs(BaseSettings):
    """Current business metrics. Override via KPI_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="KPI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    REVENUE: float = 0
    ORDERS: int = 0
    WOMEN_ARTISANS: int = 0
    PRODUCTS_LISTED: int = 0
    WEBSITE_VISITORS: int = 0
    REPEAT_CUSTOMERS: int = 0
    PARTNERSHIPS: int = 0
    SOCIAL_FOLLOWERS: int = 0


@lru_cache
def get_kpis() -> KPIs:
    return KPIs()
