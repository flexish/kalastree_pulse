"""
Daily reflection routes.

Phase 4 built the form, its validation, and the service seam
(`services/reflections.py`) Phase 6 points at Google Sheets. Phase 5 adds
the animated growing-tree / confetti experience to `reflection_success.html`
on top of that — validation and the service call are unchanged.

"Already reflected today" is tracked in the session (`last_reflection_date`)
since there's no persistence layer yet — it resets naturally the next
calendar day, or on logout, until Phase 6 gives it a durable home.
"""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.core.templating import render_template
from app.core.validation import field_errors
from app.schemas.reflection import ReflectionForm
from app.services.reflections import submit_reflection
from app.services.success_messages import get_success_message
from app.services.tree_growth import get_tree_growth_state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reflection"])


def _already_reflected_today(request: Request) -> bool:
    return request.session.get("last_reflection_date") == date.today().isoformat()


@router.get("/reflection")
async def reflection_form(request: Request):
    if not request.session.get("user_name"):
        return RedirectResponse(url="/login", status_code=303)
    if _already_reflected_today(request):
        return render_template(request, "reflection_done.html")
    return render_template(request, "reflection.html", values={}, errors={})


@router.post("/reflection")
async def reflection_submit(
    request: Request,
    rating: Annotated[int, Form()],
    # FastAPI treats an empty-string Form() value as "not provided" and
    # raises its own 422 before our handler runs unless the field has a
    # default — these need `= ""` so a blank textarea reaches our own
    # ReflectionForm validator (and its friendlier per-field error) instead.
    reason: Annotated[str, Form()] = "",
    biggest_win: Annotated[str, Form()] = "",
    biggest_blocker: Annotated[str, Form()] = "",
    tomorrow_priority: Annotated[str, Form()] = "",
    need_help: Annotated[str, Form()] = "",
    suggestions: Annotated[str, Form()] = "",
):
    user_name = request.session.get("user_name")
    if not user_name:
        return RedirectResponse(url="/login", status_code=303)

    raw = {
        "rating": rating,
        "reason": reason,
        "biggest_win": biggest_win,
        "biggest_blocker": biggest_blocker,
        "tomorrow_priority": tomorrow_priority,
        "need_help": need_help,
        "suggestions": suggestions,
    }

    try:
        form = ReflectionForm(**raw)
    except ValidationError as exc:
        errors = field_errors(exc)
        return render_template(request, "reflection.html", values=raw, errors=errors)

    submit_reflection(user_name=user_name, form=form)
    request.session["last_reflection_date"] = date.today().isoformat()
    logger.info("Reflection recorded for '%s'", user_name)
    return render_template(
        request,
        "reflection_success.html",
        success_message=get_success_message(form.rating),
        tree_state=get_tree_growth_state(),
    )
