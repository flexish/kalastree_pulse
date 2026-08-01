"""
Mission / company-goal configuration and progress calculation.

Goal *targets* are configurable, never hardcoded — an admin should be able
to change them without touching code. They're sourced from `MISSION_*`
environment variables via a dedicated settings model, kept separate from
`core.config.Settings` because these are business targets, not app
configuration. Phase 7 (Admin Dashboard) is expected to swap the storage
backend for something admin-editable at runtime (a database) without
changing how pages consume `get_mission_progress()`.

Current values (revenue, orders, artisans, ...) moved to `services/kpis.py`
in Phase 8, once "current business reality" became something more than the
mission card needed — Phase 8's tree-growth rules read the same numbers.
Keeping two independently-configured "current revenue" values would have
let them drift; `MissionGoals` now owns only targets and the deadline.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.kpis import get_kpis


class MissionGoals(BaseSettings):
    """Company goal targets for the current mission. Override via MISSION_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="MISSION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    NAME: str = "Kalastree's First Crore"
    REVENUE_TARGET: float = 10_000_000
    DEADLINE: date = Field(default_factory=lambda: date.today() + timedelta(days=120))
    ORDERS_TARGET: int = 500
    ARTISANS_TARGET: int = 50
    PRODUCTS_TARGET: int = 200
    PARTNERSHIPS_TARGET: int = 10


@lru_cache
def get_mission_goals() -> MissionGoals:
    return MissionGoals()


@dataclass
class MissionProgress:
    name: str
    revenue_current_display: str
    revenue_target_display: str
    revenue_pct: int
    days_left: int
    deadline_display: str


def format_inr(amount: float) -> str:
    """Format a number with Indian digit grouping and a rupee sign, e.g. ₹1,00,00,000."""
    whole = int(round(amount))
    sign = "-" if whole < 0 else ""
    digits = str(abs(whole))

    if len(digits) <= 3:
        grouped = digits
    else:
        last_three = digits[-3:]
        remainder = digits[:-3]
        groups = []
        while len(remainder) > 2:
            groups.insert(0, remainder[-2:])
            remainder = remainder[:-2]
        if remainder:
            groups.insert(0, remainder)
        grouped = ",".join(groups) + "," + last_three

    return f"{sign}₹{grouped}"


def _format_date(value: date) -> str:
    # Avoid platform-specific strftime flags (%-d works on Linux/Mac, %#d on
    # Windows) — build the "Month D, YYYY" string manually instead.
    return f"{value:%B} {value.day}, {value.year}"


def get_mission_progress() -> MissionProgress:
    goals = get_mission_goals()
    kpis = get_kpis()

    pct = 0
    if goals.REVENUE_TARGET > 0:
        pct = max(0, min(100, round(kpis.REVENUE / goals.REVENUE_TARGET * 100)))

    days_left = max(0, (goals.DEADLINE - date.today()).days)

    return MissionProgress(
        name=goals.NAME,
        revenue_current_display=format_inr(kpis.REVENUE),
        revenue_target_display=format_inr(goals.REVENUE_TARGET),
        revenue_pct=pct,
        days_left=days_left,
        deadline_display=_format_date(goals.DEADLINE),
    )
