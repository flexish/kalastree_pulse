"""
Team roster.

An optional allowlist gating who can sign in — off by default
(`TEAM_ROSTER_ENABLED=False`), so any correctly-formatted name still works,
exactly like before this existed. Once enabled, only names in
`config/team_roster.json` (matched case-insensitively, whitespace
collapsed) can sign in — see `config/README.md`.

Read fresh on every login attempt, not cached. Logins are infrequent
compared to the tree-growth signals that do get cached, and "a teammate
was just added to the roster but still can't sign in" is exactly the kind
of staleness worth avoiding here.
"""

import json
import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ROSTER_FILE = "config/team_roster.json"


def _roster_path() -> Path:
    return get_settings().BASE_DIR / ROSTER_FILE


def _load_roster() -> list[str]:
    path = _roster_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(
            "TEAM_ROSTER_ENABLED is on but %s doesn't exist — nobody can sign in "
            "until it's created. See config/README.md.",
            path,
        )
        return []
    except json.JSONDecodeError:
        logger.exception("Team roster file at %s is not valid JSON — treating it as empty", path)
        return []

    if not isinstance(data, list):
        logger.warning("Team roster file at %s should be a JSON array of names — ignoring it", path)
        return []

    return [str(entry).strip() for entry in data if str(entry).strip()]


def resolve_roster_name(cleaned_name: str) -> str | None:
    """Case-insensitive match against the roster. Returns the roster's own
    casing (not the visitor's typed casing) so the same person is always
    recorded identically in Sheets/analytics regardless of how they typed
    it that day — or None if the name isn't on the roster."""
    needle = cleaned_name.strip().lower()
    for entry in _load_roster():
        if entry.lower() == needle:
            return entry
    return None
