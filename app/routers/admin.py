"""
Admin routes.

Secured with a single shared password (`ADMIN_PASSWORD`), layered on top of
the existing name-based session rather than a second login system — you
must already be signed in as a team member, then this unlocks `is_admin`
in that same session. This is the same "simplest thing that works"
philosophy as Phase 2's auth; real per-admin credentials and role-based
access are explicitly future-ready work, not this phase's job.
"""

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.templating import render_template
from app.services.reflection_analytics import get_admin_stats

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


@router.get("/admin/login")
async def admin_login_page(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if _is_admin(request):
        return RedirectResponse(url="/admin", status_code=303)
    return render_template(request, "admin_login.html")


@router.post("/admin/login")
async def admin_login_submit(request: Request, password: Annotated[str, Form()] = ""):
    user_name = request.session.get("user_name")
    if not user_name:
        return RedirectResponse(url="/login", status_code=303)

    settings = get_settings()
    if not secrets.compare_digest(password, settings.ADMIN_PASSWORD):
        logger.warning("Failed admin login attempt by '%s'", user_name)
        return render_template(request, "admin_login.html", error="Incorrect password.")

    request.session["is_admin"] = True
    logger.info("Admin access granted to '%s'", user_name)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse(url="/", status_code=303)


@router.get("/admin")
async def admin_dashboard(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if not _is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    return render_template(
        request,
        "admin_dashboard.html",
        stats=get_admin_stats(),
        team_size=get_settings().TEAM_SIZE,
    )
