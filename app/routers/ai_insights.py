"""
AI Insights route.

Admin-gated, same as `/admin` and `/admin/analytics` — this surfaces the
same underlying reflection content (recurring blockers, help requests) at
a more synthesized level, which is exactly as sensitive as the analytics
page it sits alongside.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.templating import render_template
from app.services.ai_insights import get_ai_insights

router = APIRouter(tags=["insights"])


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


@router.get("/admin/insights")
async def insights_page(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    return render_template(request, "insights.html", insights=get_ai_insights())
