"""
AI Insights.

Generates the executive summary, wins/blockers, recurring issues, trends,
recommendations, sentiment, and momentum score the product spec calls
for — entirely from real computed data (`reflection_analytics.py`), no LLM
required. `AI_PROVIDER` and the provider API key settings exist so a real
OpenAI/Claude/Gemini call can be wired in later without changing this
module's public interface: `get_ai_insights()` always returns the same
`AIInsights` shape. The `_generate_summary_via_*` functions below are
placeholders, not implementations — each raises `NotImplementedError` with
a clear message, is caught, and falls back to the built-in summary. That
fallback is not a degraded mode; the heuristic summary is the actual
deliverable. An LLM, when wired in, would rephrase it more fluently — it
would not be the only thing producing insights.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import get_settings
from app.services.mission import get_mission_progress
from app.services.reflection_analytics import (
    ReflectionRecord,
    avg_rating,
    daily_participation_pct,
    get_all_reflections,
    is_meaningful,
    top_entries,
)

logger = logging.getLogger(__name__)

_TREND_RATING_THRESHOLD = 0.3
_TREND_PARTICIPATION_THRESHOLD = 10


class AISettings(BaseSettings):
    """AI provider selection. Override via AI_* env vars. Off (`none`) by default."""

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROVIDER: str = "none"  # none | openai | claude | gemini
    OPENAI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()


@dataclass
class AIInsights:
    has_data: bool
    period_label: str = ""
    executive_summary: str = ""
    top_wins: list[tuple[str, int]] = field(default_factory=list)
    top_blockers: list[tuple[str, int]] = field(default_factory=list)
    recurring_issues: list[tuple[str, int]] = field(default_factory=list)
    positive_trends: list[str] = field(default_factory=list)
    negative_trends: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    sentiment_label: str = ""
    sentiment_emoji: str = ""
    momentum_score: int = 0
    momentum_breakdown: dict[str, int] = field(default_factory=dict)
    provider_used: str = "none"


def _recurring_issues(records: list[ReflectionRecord], limit: int = 5) -> list[tuple[str, int]]:
    """Blockers mentioned on 2+ *distinct days* — a different, stricter
    signal than the admin dashboard's "top blockers by raw count," which
    can't tell a blocker mentioned 5 times in one day from one mentioned
    once a day for 5 days. Only the latter is genuinely "recurring.\""""
    by_text: dict[str, set[date]] = defaultdict(set)
    display: dict[str, str] = {}
    for r in records:
        text = r.biggest_blocker.strip()
        if not is_meaningful(text):
            continue
        key = text.lower()
        by_text[key].add(r.timestamp.date())
        display.setdefault(key, text)

    recurring = [(display[key], len(days)) for key, days in by_text.items() if len(days) >= 2]
    recurring.sort(key=lambda item: item[1], reverse=True)
    return recurring[:limit]


def _compute_trends(
    recent_avg: float | None,
    prior_avg: float | None,
    recent_participation: int,
    prior_participation: int,
) -> tuple[list[str], list[str]]:
    positive: list[str] = []
    negative: list[str] = []

    if recent_avg is not None and prior_avg is not None:
        diff = recent_avg - prior_avg
        if diff >= _TREND_RATING_THRESHOLD:
            positive.append(f"Average rating improved from {prior_avg:.1f} to {recent_avg:.1f} over the past week.")
        elif diff <= -_TREND_RATING_THRESHOLD:
            negative.append(f"Average rating dropped from {prior_avg:.1f} to {recent_avg:.1f} over the past week.")

    diff_p = recent_participation - prior_participation
    if diff_p >= _TREND_PARTICIPATION_THRESHOLD:
        positive.append(f"Participation rose from {prior_participation}% to {recent_participation}% week over week.")
    elif diff_p <= -_TREND_PARTICIPATION_THRESHOLD:
        negative.append(f"Participation fell from {prior_participation}% to {recent_participation}% week over week.")

    return positive, negative


def _build_recommendations(
    negative_trends: list[str], recurring_issues: list[tuple[str, int]], need_help_count: int
) -> list[str]:
    recommendations = []
    if negative_trends:
        recommendations.append(
            "Rating or participation dipped this week — worth a quick team check-in to understand why."
        )
    if recurring_issues:
        top_issue, days = recurring_issues[0]
        recommendations.append(
            f"“{top_issue}” has come up on {days} different days — consider addressing it "
            "directly rather than letting it recur."
        )
    if need_help_count > 0:
        recommendations.append(
            f"{need_help_count} open help request{'s' if need_help_count != 1 else ''} in the last "
            "30 days — follow up with whoever asked."
        )
    if not recommendations:
        recommendations.append("No red flags in the data right now — keep the daily reflection habit going.")
    return recommendations


def _sentiment(rating: float | None) -> tuple[str, str]:
    if rating is None:
        return "No data", "❔"
    if rating < 4:
        return "Struggling", "😟"
    if rating < 6:
        return "Cautious", "😐"
    if rating < 7.5:
        return "Steady", "🙂"
    if rating < 9:
        return "Positive", "😄"
    return "Thriving", "🚀"


def _momentum_score(recent_avg: float | None, consistency_pct: int, mission_pct: int) -> tuple[int, dict[str, int]]:
    """0-100, transparently — not a black-box AI score. Weighted 40% recent
    rating / 40% consistency (showing up regularly) / 20% mission progress.
    Rating and consistency are weighted equally and higher than mission
    progress deliberately: they're what changed *this week*, which is what
    "momentum" means; mission progress is a slow-moving number that barely
    shifts week to week and would otherwise flatten the score's ability to
    reflect a genuinely better or worse week."""
    rating_component = round((recent_avg or 0) / 10 * 100)
    consistency_component = max(0, min(100, consistency_pct))
    mission_component = max(0, min(100, mission_pct))

    score = round(rating_component * 0.4 + consistency_component * 0.4 + mission_component * 0.2)
    breakdown = {
        "Recent rating": rating_component,
        "Consistency": consistency_component,
        "Mission progress": mission_component,
    }
    return max(0, min(100, score)), breakdown


def _build_executive_summary(
    *,
    total: int,
    overall_avg: float | None,
    recent_avg: float | None,
    prior_avg: float | None,
    recent_participation: int,
    prior_participation: int,
) -> str:
    if overall_avg is None:
        return "Not enough data yet to summarize."

    lines = [
        f"Over the last 30 days, the team recorded {total} reflection{'s' if total != 1 else ''} "
        f"averaging {overall_avg:.1f}/10."
    ]

    if recent_avg is not None and prior_avg is not None:
        diff = recent_avg - prior_avg
        if diff >= _TREND_RATING_THRESHOLD:
            lines.append(f"Ratings are trending up — {prior_avg:.1f} last week to {recent_avg:.1f} this week.")
        elif diff <= -_TREND_RATING_THRESHOLD:
            lines.append(f"Ratings are trending down — {prior_avg:.1f} last week to {recent_avg:.1f} this week.")
        else:
            lines.append(f"Ratings have been steady around {recent_avg:.1f} this week.")

    if recent_participation > prior_participation:
        participation_word = "up"
    elif recent_participation < prior_participation:
        participation_word = "down"
    else:
        participation_word = "flat"
    lines.append(
        f"Participation this week is {recent_participation}%, {participation_word} from "
        f"{prior_participation}% last week."
    )

    return " ".join(lines)


def _build_heuristic_insights() -> AIInsights:
    all_records = get_all_reflections()
    if not all_records:
        return AIInsights(has_data=False)

    now = datetime.now()
    today = now.date()
    period_start = now - timedelta(days=30)
    records_30d = [r for r in all_records if r.timestamp >= period_start]

    week_start = now - timedelta(days=7)
    prior_week_start = now - timedelta(days=14)
    recent_week = [r for r in all_records if r.timestamp >= week_start]
    prior_week = [r for r in all_records if prior_week_start <= r.timestamp < week_start]

    recent_avg = avg_rating(recent_week)
    prior_avg = avg_rating(prior_week)

    settings = get_settings()
    recent_participation_days = [
        daily_participation_pct(all_records, today - timedelta(days=i), settings.TEAM_SIZE) for i in range(7)
    ]
    prior_participation_days = [
        daily_participation_pct(all_records, today - timedelta(days=i), settings.TEAM_SIZE) for i in range(7, 14)
    ]
    recent_participation = round(sum(recent_participation_days) / 7)
    prior_participation = round(sum(prior_participation_days) / 7)

    need_help_count = sum(1 for r in records_30d if is_meaningful(r.need_help))

    positive_trends, negative_trends = _compute_trends(
        recent_avg, prior_avg, recent_participation, prior_participation
    )
    recurring_issues = _recurring_issues(records_30d)
    recommendations = _build_recommendations(negative_trends, recurring_issues, need_help_count)
    sentiment_label, sentiment_emoji = _sentiment(recent_avg)
    momentum_score, momentum_breakdown = _momentum_score(
        recent_avg, recent_participation, get_mission_progress().revenue_pct
    )

    return AIInsights(
        has_data=True,
        period_label="Last 30 days",
        executive_summary=_build_executive_summary(
            total=len(records_30d),
            overall_avg=avg_rating(records_30d),
            recent_avg=recent_avg,
            prior_avg=prior_avg,
            recent_participation=recent_participation,
            prior_participation=prior_participation,
        ),
        top_wins=top_entries(records_30d, "biggest_win"),
        top_blockers=top_entries(records_30d, "biggest_blocker"),
        recurring_issues=recurring_issues,
        positive_trends=positive_trends,
        negative_trends=negative_trends,
        recommendations=recommendations,
        sentiment_label=sentiment_label,
        sentiment_emoji=sentiment_emoji,
        momentum_score=momentum_score,
        momentum_breakdown=momentum_breakdown,
        provider_used="none",
    )


def _generate_summary_via_openai(insights: AIInsights) -> str:
    raise NotImplementedError(
        "OpenAI integration is a placeholder for a future phase. Set AI_PROVIDER=none "
        "(the default) to use the built-in, data-driven summary instead of an LLM call."
    )


def _generate_summary_via_claude(insights: AIInsights) -> str:
    raise NotImplementedError(
        "Claude integration is a placeholder for a future phase. Set AI_PROVIDER=none "
        "(the default) to use the built-in, data-driven summary instead of an LLM call."
    )


def _generate_summary_via_gemini(insights: AIInsights) -> str:
    raise NotImplementedError(
        "Gemini integration is a placeholder for a future phase. Set AI_PROVIDER=none "
        "(the default) to use the built-in, data-driven summary instead of an LLM call."
    )


_PROVIDERS = {
    "openai": _generate_summary_via_openai,
    "claude": _generate_summary_via_claude,
    "gemini": _generate_summary_via_gemini,
}


def get_ai_insights() -> AIInsights:
    insights = _build_heuristic_insights()
    if not insights.has_data:
        return insights

    settings = get_ai_settings()
    provider_fn = _PROVIDERS.get(settings.PROVIDER)
    if provider_fn is None:
        return insights

    try:
        insights.executive_summary = provider_fn(insights)
        insights.provider_used = settings.PROVIDER
    except NotImplementedError as exc:
        logger.info(
            "AI provider %r not implemented yet (%s) — using the built-in summary",
            settings.PROVIDER,
            exc,
        )

    return insights
