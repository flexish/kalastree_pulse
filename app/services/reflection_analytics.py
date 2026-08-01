"""
Reflection analytics.

Reads reflections back from Google Sheets and computes the aggregate
numbers the admin dashboard (Phase 7) and analytics page (Phase 9) show.
Phase 6 only ever wrote to Sheets — this is the read path it didn't need.
Owning all of it here keeps routers thin, and gives Phase 10 (AI insights)
the same primitives to build on instead of re-parsing the sheet itself.

If Google Sheets isn't configured, or has no rows yet, everything here
returns an explicit "no data" result rather than raising — reflections are
the only real data source, and there may honestly be none yet. Pages are
expected to render a clear empty state for that, not crash.
"""

import csv
import io
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.core.config import get_settings
from app.services.google_sheets import get_worksheet

logger = logging.getLogger(__name__)

# Free-text "need help" answers that mean "no, nothing" rather than an
# actual request — filtered out so the admin dashboard only surfaces real
# asks, not every row.
_NEGATIVE_RESPONSES = {
    "none",
    "no",
    "n/a",
    "na",
    "nothing",
    "nothing right now",
    "nothing much",
    "nothing for now",
    "all good",
    "all good for now",
    "nope",
    "-",
    "none right now",
    "not really",
}

_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class ReflectionRecord:
    timestamp: datetime
    name: str
    rating: int
    reason: str
    biggest_win: str
    biggest_blocker: str
    tomorrow_priority: str
    need_help: str
    suggestions: str


@dataclass
class AdminStats:
    has_data: bool
    total_reflections: int = 0
    today_avg_rating: float | None = None
    weekly_avg_rating: float | None = None
    monthly_avg_rating: float | None = None
    participation_pct: int = 0
    completion_pct: int = 0
    need_help_entries: list[ReflectionRecord] = field(default_factory=list)
    top_blockers: list[tuple[str, int]] = field(default_factory=list)
    top_wins: list[tuple[str, int]] = field(default_factory=list)
    top_priorities: list[tuple[str, int]] = field(default_factory=list)


def is_meaningful(text: str) -> bool:
    cleaned = text.strip()
    return bool(cleaned) and cleaned.lower() not in _NEGATIVE_RESPONSES


def get_all_reflections() -> list[ReflectionRecord]:
    worksheet = get_worksheet()
    if worksheet is None:
        return []

    try:
        rows = worksheet.get_all_values()
    except Exception:
        logger.exception("Failed to read reflections from Google Sheets")
        return []

    records: list[ReflectionRecord] = []
    for row in rows[1:]:  # skip header
        if len(row) < 9:
            continue
        try:
            timestamp = datetime.strptime(row[0], _TIMESTAMP_FORMAT)
            rating = int(row[2])
        except ValueError:
            continue
        records.append(
            ReflectionRecord(
                timestamp=timestamp,
                name=row[1],
                rating=rating,
                reason=row[3],
                biggest_win=row[4],
                biggest_blocker=row[5],
                tomorrow_priority=row[6],
                need_help=row[7],
                suggestions=row[8],
            )
        )
    return records


def avg_rating(records: list[ReflectionRecord]) -> float | None:
    if not records:
        return None
    return sum(r.rating for r in records) / len(records)


def top_entries(
    records: list[ReflectionRecord], field_name: str, limit: int = 5
) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for record in records:
        text = getattr(record, field_name).strip()
        if not is_meaningful(text):
            continue
        key = text.lower()
        counts[key] += 1
        display.setdefault(key, text)
    return [(display[key], count) for key, count in counts.most_common(limit)]


def get_admin_stats() -> AdminStats:
    records = get_all_reflections()
    if not records:
        return AdminStats(has_data=False)

    settings = get_settings()
    now = datetime.now()
    today = now.date()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    today_records = [r for r in records if r.timestamp.date() == today]
    week_records = [r for r in records if r.timestamp >= week_start]
    month_records = [r for r in records if r.timestamp >= month_start]

    participation_pct = daily_participation_pct(records, today, settings.TEAM_SIZE)

    # "Completion" is deliberately a different number from today's snapshot:
    # the trailing 7-day average of daily participation, i.e. how
    # consistently — not just today — the team has been showing up.
    daily_pcts = [
        daily_participation_pct(records, today - timedelta(days=offset), settings.TEAM_SIZE)
        for offset in range(7)
    ]
    completion_pct = round(sum(daily_pcts) / len(daily_pcts)) if daily_pcts else 0

    need_help_entries = [r for r in month_records if is_meaningful(r.need_help)]
    need_help_entries.sort(key=lambda r: r.timestamp, reverse=True)

    return AdminStats(
        has_data=True,
        total_reflections=len(records),
        today_avg_rating=avg_rating(today_records),
        weekly_avg_rating=avg_rating(week_records),
        monthly_avg_rating=avg_rating(month_records),
        participation_pct=participation_pct,
        completion_pct=completion_pct,
        need_help_entries=need_help_entries[:5],
        top_blockers=top_entries(month_records, "biggest_blocker"),
        top_wins=top_entries(month_records, "biggest_win"),
        top_priorities=top_entries(month_records, "tomorrow_priority"),
    )


def daily_participation_pct(
    records: list[ReflectionRecord], day: date, team_size: int
) -> int:
    if team_size <= 0:
        return 0
    names_that_day = {r.name for r in records if r.timestamp.date() == day}
    return min(100, round(len(names_that_day) / team_size * 100))


# ==============================================================================
# Phase 9 — Analytics: trend charts, heatmap, distribution, comparison, filters
# ==============================================================================


@dataclass
class TrendBucket:
    label: str
    period_start: date
    avg_rating: float | None
    count: int


@dataclass
class ChartPoint:
    x: float
    y: float
    label: str


@dataclass
class HeatmapDay:
    day: date
    pct: int
    count: int
    opacity: float


@dataclass
class MemberStats:
    name: str
    count: int
    avg_rating: float | None


def filter_reflections(
    records: list[ReflectionRecord],
    *,
    member: str | None = None,
    search: str | None = None,
) -> list[ReflectionRecord]:
    result = records
    if member:
        result = [r for r in result if r.name == member]
    if search:
        needle = search.strip().lower()
        if needle:
            result = [
                r
                for r in result
                if needle in r.name.lower()
                or needle in r.reason.lower()
                or needle in r.biggest_win.lower()
                or needle in r.biggest_blocker.lower()
                or needle in r.tomorrow_priority.lower()
                or needle in r.need_help.lower()
                or needle in r.suggestions.lower()
            ]
    return result


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())  # Monday


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _add_month(day: date) -> date:
    if day.month == 12:
        return day.replace(year=day.year + 1, month=1)
    return day.replace(month=day.month + 1)


def _bucket_by_day(
    records: list[ReflectionRecord], start_date: date, end_date: date
) -> list[TrendBucket]:
    by_day: dict[date, list[ReflectionRecord]] = defaultdict(list)
    for r in records:
        by_day[r.timestamp.date()].append(r)

    buckets = []
    day = start_date
    while day <= end_date:
        day_records = by_day.get(day, [])
        buckets.append(
            TrendBucket(
                label=f"{day:%b} {day.day}",
                period_start=day,
                avg_rating=avg_rating(day_records),
                count=len(day_records),
            )
        )
        day += timedelta(days=1)
    return buckets


def _bucket_by_week(
    records: list[ReflectionRecord], start_date: date, end_date: date
) -> list[TrendBucket]:
    by_week: dict[date, list[ReflectionRecord]] = defaultdict(list)
    for r in records:
        by_week[_week_start(r.timestamp.date())].append(r)

    buckets = []
    week = _week_start(start_date)
    last_week = _week_start(end_date)
    while week <= last_week:
        week_records = by_week.get(week, [])
        buckets.append(
            TrendBucket(
                label=f"Week of {week:%b} {week.day}",
                period_start=week,
                avg_rating=avg_rating(week_records),
                count=len(week_records),
            )
        )
        week += timedelta(days=7)
    return buckets


def _bucket_by_month(
    records: list[ReflectionRecord], start_date: date, end_date: date
) -> list[TrendBucket]:
    by_month: dict[date, list[ReflectionRecord]] = defaultdict(list)
    for r in records:
        by_month[_month_start(r.timestamp.date())].append(r)

    buckets = []
    month = _month_start(start_date)
    last_month = _month_start(end_date)
    while month <= last_month:
        month_records = by_month.get(month, [])
        buckets.append(
            TrendBucket(
                label=f"{month:%b %Y}",
                period_start=month,
                avg_rating=avg_rating(month_records),
                count=len(month_records),
            )
        )
        month = _add_month(month)
    return buckets


def bucket_trend(
    records: list[ReflectionRecord], start_date: date, end_date: date, period: str
) -> list[TrendBucket]:
    if period == "week":
        return _bucket_by_week(records, start_date, end_date)
    if period == "month":
        return _bucket_by_month(records, start_date, end_date)
    return _bucket_by_day(records, start_date, end_date)


def build_line_segments(
    buckets: list[TrendBucket], width: int = 560, height: int = 160, pad_x: int = 20, pad_y: int = 16
) -> list[list[ChartPoint]]:
    """Split into contiguous segments so buckets with no data become a gap
    in the line rather than a fabricated interpolation across them. Uses a
    fixed 1-10 y-axis (rating's real range) rather than an auto-scaled one,
    so chart shape is comparable across different periods/date ranges."""
    n = len(buckets)
    if n == 0:
        return []

    y_min, y_max = 1, 10
    points: list[ChartPoint | None] = []
    for i, bucket in enumerate(buckets):
        if bucket.avg_rating is None:
            points.append(None)
            continue
        x = pad_x + (i / max(1, n - 1)) * (width - 2 * pad_x)
        y = pad_y + (1 - (bucket.avg_rating - y_min) / (y_max - y_min)) * (height - 2 * pad_y)
        points.append(ChartPoint(x=round(x, 1), y=round(y, 1), label=f"{bucket.label}: {bucket.avg_rating:.1f}"))

    segments: list[list[ChartPoint]] = []
    current: list[ChartPoint] = []
    for p in points:
        if p is None:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(p)
    if current:
        segments.append(current)
    return segments


def get_participation_heatmap(
    records: list[ReflectionRecord], start_date: date, end_date: date, team_size: int
) -> list[HeatmapDay]:
    by_day: dict[date, set[str]] = defaultdict(set)
    for r in records:
        by_day[r.timestamp.date()].add(r.name)

    result = []
    day = start_date
    while day <= end_date:
        names = by_day.get(day, set())
        pct = daily_participation_pct(records, day, team_size)
        # A floor so a real 0%-participation day still shows a faint,
        # clickable cell distinct from the transparent padding cells
        # build_heatmap_grid adds around the edges of partial weeks.
        opacity = round(0.06 + (pct / 100) * 0.84, 2)
        result.append(HeatmapDay(day=day, pct=pct, count=len(names), opacity=opacity))
        day += timedelta(days=1)
    return result


def build_heatmap_grid(days: list[HeatmapDay]) -> list[list[HeatmapDay | None]]:
    """GitHub-style grid: a list of week-columns, each 7 day-cells (Mon-Sun),
    padded with None at the start/end so partial weeks still line up."""
    if not days:
        return []

    pad_start = days[0].day.weekday()
    padded: list[HeatmapDay | None] = [None] * pad_start + list(days)
    remainder = len(padded) % 7
    if remainder:
        padded += [None] * (7 - remainder)

    return [padded[i : i + 7] for i in range(0, len(padded), 7)]


def get_rating_distribution(records: list[ReflectionRecord]) -> list[tuple[int, int]]:
    counts = Counter(r.rating for r in records)
    return [(rating, counts.get(rating, 0)) for rating in range(1, 11)]


def get_member_comparison(records: list[ReflectionRecord]) -> list[MemberStats]:
    by_name: dict[str, list[ReflectionRecord]] = defaultdict(list)
    for r in records:
        by_name[r.name].append(r)

    members = [
        MemberStats(name=name, count=len(recs), avg_rating=avg_rating(recs))
        for name, recs in by_name.items()
    ]
    members.sort(key=lambda m: m.count, reverse=True)
    return members


def to_csv(records: list[ReflectionRecord]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Timestamp",
            "Name",
            "Rating",
            "Reason",
            "Biggest Win",
            "Biggest Blocker",
            "Tomorrow Priority",
            "Need Help",
            "Suggestions",
        ]
    )
    for r in records:
        writer.writerow(
            [
                r.timestamp.strftime(_TIMESTAMP_FORMAT),
                r.name,
                r.rating,
                r.reason,
                r.biggest_win,
                r.biggest_blocker,
                r.tomorrow_priority,
                r.need_help,
                r.suggestions,
            ]
        )
    return output.getvalue()
