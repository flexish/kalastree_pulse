"""
Mission Dashboard route.

The spec's "hero page" — mission name, revenue progress, days left, tree
and forest growth, milestones, completion %. Visible to every signed-in
team member, not admin-gated, same precedent as `/growth`: this is meant
to motivate the whole team every morning, not report to admins.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.templating import render_template
from app.services.kpis import get_kpis
from app.services.mission import format_inr, get_mission_goals, get_mission_progress
from app.services.tree_growth import ELEMENT_TYPES, get_tree_growth_state

router = APIRouter(tags=["mission"])


@router.get("/mission")
async def mission_dashboard(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)

    goals = get_mission_goals()
    progress = get_mission_progress()
    kpis = get_kpis()
    tree_state = get_tree_growth_state()

    remaining_display = format_inr(max(0, goals.REVENUE_TARGET - kpis.REVENUE))
    milestones = [
        description
        for element in ELEMENT_TYPES
        for description in tree_state.unlocked_descriptions.get(element, [])
    ]

    return render_template(
        request,
        "mission.html",
        goals=goals,
        progress=progress,
        tree_state=tree_state,
        remaining_display=remaining_display,
        milestones=milestones,
    )
