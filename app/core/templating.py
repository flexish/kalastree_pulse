"""
Shared Jinja2 environment and render helper.

Every route renders through `render_template()` instead of building its own
`Jinja2Templates` instance, so common context — app identity, environment,
and the signed-in user's name — is injected exactly once instead of being
repeated in every router.
"""

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

settings = get_settings()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


def render_template(request: Request, template_name: str, **context: Any):
    base_context = {
        "app_name": settings.APP_NAME,
        "app_tagline": settings.APP_TAGLINE,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "user_name": request.session.get("user_name"),
    }
    base_context.update(context)
    return templates.TemplateResponse(request, template_name, base_context)
