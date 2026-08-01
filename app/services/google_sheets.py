"""
Google Sheets client.

The rest of the app only ever calls `is_sheets_configured()` and
`append_reflection_row()` — nothing else needs to know the backing store is
Sheets specifically. That's deliberate: swapping this for Postgres/Supabase
later (see README's "Future Ready" notes) means replacing this one file,
not touching the reflection router or schema.

If Sheets isn't configured — `GOOGLE_SHEETS_ENABLED=false` (the default),
no spreadsheet ID, or a missing credentials file — every function here
becomes a safe no-op that logs instead of raising. The app must keep
working without Sheets set up; a submitted reflection should never be lost
just because an external API hiccupped or a team hasn't finished setup.
"""

import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import gspread
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import get_settings

logger = logging.getLogger(__name__)

HEADER_ROW = [
    "Timestamp",
    "Name",
    "Rating",
    "Reason",
    "Biggest Win",
    "Biggest Blocker",
    "Tomorrow Priority",
    "Need Help",
    "Suggestions",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsSettings(BaseSettings):
    """Google Sheets connection settings. Override via GOOGLE_SHEETS_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_SHEETS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENABLED: bool = False
    CREDENTIALS_FILE: str = "credentials/service-account.json"
    SPREADSHEET_ID: str = ""
    WORKSHEET_NAME: str = "Reflections"


@lru_cache
def get_sheets_settings() -> GoogleSheetsSettings:
    return GoogleSheetsSettings()


def _resolve_credentials_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else get_settings().BASE_DIR / path


def is_sheets_configured() -> bool:
    settings = get_sheets_settings()
    if not settings.ENABLED:
        return False
    if not settings.SPREADSHEET_ID:
        logger.warning("Google Sheets is enabled but GOOGLE_SHEETS_SPREADSHEET_ID is not set")
        return False
    if not _resolve_credentials_path(settings.CREDENTIALS_FILE).exists():
        logger.warning(
            "Google Sheets is enabled but the credentials file was not found: %s",
            _resolve_credentials_path(settings.CREDENTIALS_FILE),
        )
        return False
    return True


@lru_cache
def _get_client() -> gspread.Client | None:
    if not is_sheets_configured():
        return None
    settings = get_sheets_settings()
    try:
        return gspread.service_account(
            filename=str(_resolve_credentials_path(settings.CREDENTIALS_FILE)),
            scopes=_SCOPES,
        )
    except Exception:
        logger.exception("Failed to authorize the Google Sheets client")
        return None


def get_worksheet() -> gspread.Worksheet | None:
    client = _get_client()
    if client is None:
        return None

    settings = get_sheets_settings()
    try:
        spreadsheet = client.open_by_key(settings.SPREADSHEET_ID)
    except Exception:
        logger.exception("Failed to open spreadsheet %r", settings.SPREADSHEET_ID)
        return None

    try:
        return spreadsheet.worksheet(settings.WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        try:
            worksheet = spreadsheet.add_worksheet(
                title=settings.WORKSHEET_NAME, rows=1000, cols=len(HEADER_ROW)
            )
            worksheet.append_row(HEADER_ROW)
            return worksheet
        except Exception:
            logger.exception("Failed to create worksheet %r", settings.WORKSHEET_NAME)
            return None
    except Exception:
        logger.exception("Failed to open worksheet %r", settings.WORKSHEET_NAME)
        return None


def append_reflection_row(
    *,
    timestamp: datetime,
    user_name: str,
    rating: int,
    reason: str,
    biggest_win: str,
    biggest_blocker: str,
    tomorrow_priority: str,
    need_help: str,
    suggestions: str,
) -> bool:
    """Append one reflection as a row. Returns False (never raises) if Sheets
    isn't configured or the write fails — callers should fall back to their
    own log/audit trail rather than fail the user's submission."""
    worksheet = get_worksheet()
    if worksheet is None:
        return False

    try:
        worksheet.append_row(
            [
                timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                user_name,
                rating,
                reason,
                biggest_win,
                biggest_blocker,
                tomorrow_priority,
                need_help,
                suggestions,
            ]
        )
        return True
    except Exception:
        logger.exception("Failed to append reflection row to Google Sheets")
        return False
