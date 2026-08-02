"""
Page routes.

Server-rendered Jinja2 pages. Later phases add reflection, admin, and
analytics routes as their own routers rather than growing this file
indefinitely.
"""

from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.templating import render_template
from app.services.mission import get_mission_progress
from app.services.quotes import get_daily_quote
from app.services.tree_growth import get_tree_growth_state

router = APIRouter(tags=["pages"])


def _greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@router.get("/")
async def homepage(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)

    now = datetime.now()
    last = request.session.get("last_reflection") or {}
    already_reflected = (
        last.get("user") == request.session.get("user_name")
        and last.get("date") == now.date().isoformat()
    )

    return render_template(
        request,
        "index.html",
        greeting=_greeting(now.hour),
        today_display=f"{now:%A}, {now:%B} {now.day}, {now.year}",
        mission=get_mission_progress(),
        quote=get_daily_quote(now.date()),
        already_reflected=already_reflected,
        streak_days=1 if already_reflected else 0,
        tree_state=get_tree_growth_state(),
    )
