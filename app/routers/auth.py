"""
Authentication routes.

Phase 2 auth is intentionally minimal: a name identifies who is checking
in, held in a signed session cookie (Starlette's `SessionMiddleware`) — no
passwords, no user table yet. `Settings.SECRET_KEY` signs that cookie today
and is the same key later phases (JWT, RBAC) build on top of.

An optional roster check (`services/team_roster.py`) sits after format
validation: off by default, so this is still purely additive to Phase 2's
original behavior until `TEAM_ROSTER_ENABLED=True` and the roster file is
populated.
"""

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ValidationError, field_validator

from app.core.config import get_settings
from app.core.templating import render_template
from app.core.validation import first_error_message
from app.services.team_roster import resolve_roster_name

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")


class LoginForm(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not NAME_PATTERN.match(cleaned):
            raise ValueError(
                "Enter your name using 2-50 letters, spaces, hyphens, or apostrophes."
            )
        return cleaned


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("user_name"):
        return RedirectResponse(url="/", status_code=303)
    return render_template(request, "login.html")


@router.post("/login")
async def login_submit(request: Request, name: Annotated[str, Form()]):
    try:
        form = LoginForm(name=name)
    except ValidationError as exc:
        error = first_error_message(exc)
        return render_template(request, "login.html", error=error, name=name)

    signed_in_name = form.name
    if get_settings().TEAM_ROSTER_ENABLED:
        matched_name = resolve_roster_name(form.name)
        if matched_name is None:
            logger.warning("Login rejected — '%s' is not on the team roster", form.name)
            return render_template(
                request,
                "login.html",
                error="That name isn't on the team list. Check the spelling, or ask an admin to add you.",
                name=name,
            )
        signed_in_name = matched_name

    # Admin status must never carry over to whoever signs in next on a
    # shared device — it's the one session flag that's a real privilege,
    # not just UI state. `last_reflection` (below) is left alone: it's
    # already keyed by name, so it self-corrects for a *different* person
    # and still correctly says "already reflected" if the same person logs
    # back in later the same day.
    request.session.pop("is_admin", None)
    request.session["user_name"] = signed_in_name
    logger.info("User '%s' signed in", signed_in_name)
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    user_name = request.session.pop("user_name", None)
    request.session.pop("is_admin", None)
    if user_name:
        logger.info("User '%s' signed out", user_name)
    return RedirectResponse(url="/login", status_code=303)
