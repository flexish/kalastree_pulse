"""
Kalastree Pulse — FastAPI application entrypoint.

Wires together configuration, logging, static assets, templates, and
routers. Kept intentionally thin: startup concerns live here, request
handling lives in `app/routers/`, business logic lives in `app/services/`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import Scope

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.routers import admin, ai_insights, analytics, auth, growth, mission, pages, reflections

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "%s v%s starting up (environment=%s, debug=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )
    yield
    logger.info("%s shutting down", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=settings.is_production,
)

class CachedStaticFiles(StaticFiles):
    """Adds a Cache-Control header so browsers stop re-fetching unchanged
    CSS/JS on every navigation — skipped in DEBUG so local edits during
    development are never masked by a stale cached asset."""

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        if not settings.DEBUG and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response


app.mount("/static", CachedStaticFiles(directory=settings.STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(reflections.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(ai_insights.router)
app.include_router(growth.router)
app.include_router(mission.router)
app.include_router(pages.router)
