"""
Tree growth rules engine.

Maps configurable KPI/participation thresholds to which tree elements are
unlocked — leaves, branches, flowers, fruits, birds — per
`config/tree_rules.json`. The mapping itself is never hardcoded in Python;
admins edit that file to add, remove, or retune rules without a code
change or deploy (see `config/README.md`). This module only knows how to
*evaluate* rules against the current signals, not what the rules are.

Results are cached for a short window (`_CACHE_TTL_SECONDS`) because one of
the signals (today's participation) comes from `reflection_analytics`,
which reads Google Sheets — without a cache, every home-dashboard and
every reflection-success page view would trigger a live Sheets read. A
tree that's a minute stale is unnoticeable; a Sheets call on every page
load is not free.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.services.kpis import get_kpis
from app.services.mission import get_mission_progress
from app.services.reflection_analytics import AdminStats, get_admin_stats

logger = logging.getLogger(__name__)

RULES_FILE = "config/tree_rules.json"
ELEMENT_TYPES = ("leaves", "branches", "flowers", "fruits", "birds")
_CACHE_TTL_SECONDS = 60

# "Forest growth" (Phase 11) is a distinct signal from the tree's KPI-driven
# growth: it tracks cumulative team practice over time (how many
# reflections have ever been submitted), not business milestones. One
# small tree per 5 reflections, capped so the forest stays legible.
FOREST_TREES_PER_REFLECTIONS = 5
MAX_FOREST_TREES = 12


@dataclass
class TreeGrowthState:
    leaf_count: int = 0
    branch_count: int = 0
    flower_count: int = 0
    fruit_count: int = 0
    bird_count: int = 0
    total_unlocked: int = 0
    stage_label: str = "🌱 Seedling stage"
    unlocked_descriptions: dict[str, list[str]] = field(default_factory=dict)
    total_reflections: int = 0
    forest_size: int = 0


def _rules_path() -> Path:
    return get_settings().BASE_DIR / RULES_FILE


def _load_rules() -> dict[str, list[dict]]:
    path = _rules_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(
            "Tree growth rules file not found at %s — tree will show baseline growth only",
            path,
        )
        return {element: [] for element in ELEMENT_TYPES}
    except json.JSONDecodeError:
        logger.exception("Tree growth rules file at %s is not valid JSON — ignoring", path)
        return {element: [] for element in ELEMENT_TYPES}

    return {element: data.get(element, []) for element in ELEMENT_TYPES}


def _forest_size(total_reflections: int) -> int:
    if total_reflections <= 0:
        return 0
    return min(MAX_FOREST_TREES, 1 + total_reflections // FOREST_TREES_PER_REFLECTIONS)


def _get_signals(admin_stats: AdminStats) -> dict[str, float]:
    kpis = get_kpis()
    mission = get_mission_progress()

    return {
        "revenue": kpis.REVENUE,
        "orders": kpis.ORDERS,
        "women_artisans": kpis.WOMEN_ARTISANS,
        "products_listed": kpis.PRODUCTS_LISTED,
        "website_visitors": kpis.WEBSITE_VISITORS,
        "repeat_customers": kpis.REPEAT_CUSTOMERS,
        "partnerships": kpis.PARTNERSHIPS,
        "social_followers": kpis.SOCIAL_FOLLOWERS,
        "participation_today_pct": admin_stats.participation_pct if admin_stats.has_data else 0,
        "mission_progress_pct": mission.revenue_pct,
    }


def _stage_label(total_unlocked: int) -> str:
    if total_unlocked == 0:
        return "🌱 Seedling stage"
    if total_unlocked <= 3:
        return "🌿 Growing stage"
    if total_unlocked <= 7:
        return "🌳 Flourishing stage"
    return "✨ Magnificent stage"


def _compute_tree_growth_state() -> TreeGrowthState:
    rules = _load_rules()
    admin_stats = get_admin_stats()
    signals = _get_signals(admin_stats)

    counts = {element: 0 for element in ELEMENT_TYPES}
    descriptions: dict[str, list[str]] = {element: [] for element in ELEMENT_TYPES}

    for element in ELEMENT_TYPES:
        for rule in rules.get(element, []):
            kpi_key = rule.get("kpi")
            threshold = rule.get("threshold")
            description = rule.get("description", "")
            if kpi_key not in signals or threshold is None:
                logger.warning("Skipping invalid tree growth rule: %r", rule)
                continue
            if signals[kpi_key] >= threshold:
                counts[element] += 1
                descriptions[element].append(description)

    total_unlocked = sum(counts.values())
    total_reflections = admin_stats.total_reflections if admin_stats.has_data else 0

    return TreeGrowthState(
        leaf_count=counts["leaves"],
        branch_count=counts["branches"],
        flower_count=counts["flowers"],
        fruit_count=counts["fruits"],
        bird_count=counts["birds"],
        total_unlocked=total_unlocked,
        stage_label=_stage_label(total_unlocked),
        unlocked_descriptions=descriptions,
        total_reflections=total_reflections,
        forest_size=_forest_size(total_reflections),
    )


_cache: dict[str, tuple[float, TreeGrowthState]] = {}


def get_tree_growth_state() -> TreeGrowthState:
    now = time.monotonic()
    cached = _cache.get("state")
    if cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    state = _compute_tree_growth_state()
    _cache["state"] = (now, state)
    return state
