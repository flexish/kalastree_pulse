"""
Reflection submission service.

Every submission is logged first — a cheap, reliable audit trail that never
depends on an external API being reachable. Google Sheets (`google_sheets.py`)
is then attempted as the durable store; if it isn't configured or the write
fails, the submission still succeeds for the user (they already saw the
success screen) and the log line is what's left to fall back on. Phase 7's
admin dashboard and Phase 9's analytics are expected to read from Sheets,
not this log.
"""

import logging
from datetime import datetime

from app.schemas.reflection import ReflectionForm
from app.services.google_sheets import append_reflection_row

logger = logging.getLogger(__name__)


def submit_reflection(user_name: str, form: ReflectionForm) -> None:
    logger.info(
        "Reflection | user=%s rating=%s reason=%r win=%r blocker=%r priority=%r "
        "help=%r suggestions=%r",
        user_name,
        form.rating,
        form.reason,
        form.biggest_win,
        form.biggest_blocker,
        form.tomorrow_priority,
        form.need_help,
        form.suggestions,
    )

    written = append_reflection_row(
        timestamp=datetime.now(),
        user_name=user_name,
        rating=form.rating,
        reason=form.reason,
        biggest_win=form.biggest_win,
        biggest_blocker=form.biggest_blocker,
        tomorrow_priority=form.tomorrow_priority,
        need_help=form.need_help,
        suggestions=form.suggestions,
    )
    if not written:
        logger.warning(
            "Reflection for '%s' was not persisted to Google Sheets (log only)", user_name
        )
