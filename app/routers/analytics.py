"""
Analytics routes.

Admin-gated with the same `is_admin` session flag as Phase 7's `/admin` —
the reflection table, search, and CSV export expose individual free-text
entries, not just aggregates, which is more sensitive than the
company-wide KPI transparency on `/growth`. Everything here reads through
`services/reflection_analytics.py`; nothing on this page writes anything.

The page and the CSV export accept the same query params (`start`, `end`,
`member`, `q`) and resolve them identically via `_load_filtered()`, so
"export what I'm currently looking at" always matches what's on screen.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse, Response

from app.core.config import get_settings
from app.core.templating import render_template
from app.services.reflection_analytics import (
    ReflectionRecord,
    build_heatmap_grid,
    build_line_segments,
    bucket_trend,
    filter_reflections,
    get_all_reflections,
    get_member_comparison,
    get_participation_heatmap,
    get_rating_distribution,
    to_csv,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])

DEFAULT_WINDOW_DAYS = 90
VALID_PERIODS = {"day", "week", "month"}


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def _resolve_window(start: str | None, end: str | None) -> tuple[date, date]:
    today = date.today()
    try:
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        end_date = today
    try:
        start_date = (
            date.fromisoformat(start) if start else end_date - timedelta(days=DEFAULT_WINDOW_DAYS)
        )
    except ValueError:
        start_date = end_date - timedelta(days=DEFAULT_WINDOW_DAYS)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _load_filtered(
    start: str | None, end: str | None, member: str | None, search: str | None
) -> tuple[date, date, list[ReflectionRecord], list[ReflectionRecord]]:
    start_date, end_date = _resolve_window(start, end)
    all_records = get_all_reflections()
    windowed = [r for r in all_records if start_date <= r.timestamp.date() <= end_date]
    filtered = filter_reflections(windowed, member=member, search=search)
    return start_date, end_date, all_records, filtered


@router.get("/admin/analytics")
async def analytics_page(
    request: Request,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    member: str | None = Query(default=None),
    q: str | None = Query(default=None),
    period: str = Query(default="day"),
):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    if period not in VALID_PERIODS:
        period = "day"

    start_date, end_date, all_records, filtered = _load_filtered(start, end, member, q)
    settings = get_settings()

    trend_buckets = bucket_trend(filtered, start_date, end_date, period)
    trend_segments = build_line_segments(trend_buckets)

    heatmap_days = get_participation_heatmap(filtered, start_date, end_date, settings.TEAM_SIZE)
    heatmap_weeks = build_heatmap_grid(heatmap_days)

    distribution = get_rating_distribution(filtered)
    max_distribution_count = max((count for _, count in distribution), default=0)

    return render_template(
        request,
        "analytics.html",
        start_date=start_date,
        end_date=end_date,
        member=member or "",
        search=q or "",
        period=period,
        trend_segments=trend_segments,
        heatmap_weeks=heatmap_weeks,
        distribution=distribution,
        max_distribution_count=max_distribution_count,
        members=get_member_comparison(filtered),
        all_member_names=sorted({r.name for r in all_records}),
        results=sorted(filtered, key=lambda r: r.timestamp, reverse=True),
        total_records=len(all_records),
        filtered_count=len(filtered),
    )


@router.get("/admin/analytics/export.csv")
async def analytics_export(
    request: Request,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    member: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    start_date, end_date, _all_records, filtered = _load_filtered(start, end, member, q)
    filtered.sort(key=lambda r: r.timestamp)

    logger.info(
        "Admin '%s' exported %d reflections (%s to %s) as CSV",
        request.session.get("user_name"),
        len(filtered),
        start_date,
        end_date,
    )

    filename = f"kalastree-reflections_{start_date}_{end_date}.csv"
    return Response(
        content=to_csv(filtered),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
