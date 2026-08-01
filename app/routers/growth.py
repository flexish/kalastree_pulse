"""
Business growth routes.

Company-wide KPI transparency — visible to every signed-in team member,
not admin-gated, consistent with the mission card already on the home
dashboard. This is the page the product spec calls the "Business Growth
Dashboard": what the numbers are, and why the tree looks the way it does.
"""

from dataclasses import dataclass

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.templating import render_template
from app.services.kpis import KPIs, get_kpis
from app.services.mission import MissionGoals, format_inr, get_mission_goals
from app.services.tree_growth import get_tree_growth_state

router = APIRouter(tags=["growth"])


@dataclass
class KPITile:
    label: str
    value_display: str
    target_display: str | None = None
    pct: int | None = None


def _pct_of(current: float, target: float) -> int | None:
    if target <= 0:
        return None
    return max(0, min(100, round(current / target * 100)))


def _build_kpi_tiles(kpis: KPIs, goals: MissionGoals) -> list[KPITile]:
    return [
        KPITile(
            "Revenue",
            format_inr(kpis.REVENUE),
            format_inr(goals.REVENUE_TARGET),
            _pct_of(kpis.REVENUE, goals.REVENUE_TARGET),
        ),
        KPITile(
            "Orders",
            f"{kpis.ORDERS:,}",
            f"{goals.ORDERS_TARGET:,}",
            _pct_of(kpis.ORDERS, goals.ORDERS_TARGET),
        ),
        KPITile(
            "Women Artisans",
            f"{kpis.WOMEN_ARTISANS:,}",
            f"{goals.ARTISANS_TARGET:,}",
            _pct_of(kpis.WOMEN_ARTISANS, goals.ARTISANS_TARGET),
        ),
        KPITile(
            "Products Listed",
            f"{kpis.PRODUCTS_LISTED:,}",
            f"{goals.PRODUCTS_TARGET:,}",
            _pct_of(kpis.PRODUCTS_LISTED, goals.PRODUCTS_TARGET),
        ),
        KPITile(
            "Partnerships",
            f"{kpis.PARTNERSHIPS:,}",
            f"{goals.PARTNERSHIPS_TARGET:,}",
            _pct_of(kpis.PARTNERSHIPS, goals.PARTNERSHIPS_TARGET),
        ),
        # No target in the original "Company Goals" list — these are
        # tracked purely as tree-growth signals, shown as plain counters.
        KPITile("Website Visitors", f"{kpis.WEBSITE_VISITORS:,}"),
        KPITile("Repeat Customers", f"{kpis.REPEAT_CUSTOMERS:,}"),
        KPITile("Social Followers", f"{kpis.SOCIAL_FOLLOWERS:,}"),
    ]


@router.get("/growth")
async def growth_dashboard(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)

    return render_template(
        request,
        "growth.html",
        kpi_tiles=_build_kpi_tiles(get_kpis(), get_mission_goals()),
        tree_state=get_tree_growth_state(),
    )
