"""
Standalone connectivity check for the Google Sheets integration.

Run this after setting GOOGLE_SHEETS_* in .env and sharing your Sheet with
the service account's email, to confirm the app can actually reach it
before relying on it from the reflection form:

    python scripts/check_google_sheets.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.google_sheets import (  # noqa: E402
    get_sheets_settings,
    get_worksheet,
    is_sheets_configured,
)


def main() -> int:
    if not is_sheets_configured():
        print(
            "Google Sheets is not configured (or misconfigured).\n"
            "Check GOOGLE_SHEETS_ENABLED, GOOGLE_SHEETS_SPREADSHEET_ID, and "
            "GOOGLE_SHEETS_CREDENTIALS_FILE in .env — see the log output above "
            "for which one."
        )
        return 1

    settings = get_sheets_settings()
    print(
        f"Connecting to spreadsheet {settings.SPREADSHEET_ID!r}, "
        f"worksheet {settings.WORKSHEET_NAME!r}..."
    )

    worksheet = get_worksheet()
    if worksheet is None:
        print(
            "Failed to open the worksheet. Check the log output above — the "
            "most common cause is the service account's email not having "
            "been given Editor access to the sheet."
        )
        return 1

    print(f"Connected. Worksheet title={worksheet.title!r}, row_count={worksheet.row_count}.")
    print("Google Sheets is set up correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
