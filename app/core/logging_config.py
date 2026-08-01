"""
Application-wide logging setup.

We configure the *root* logger once at startup so every module can simply do
`logging.getLogger(__name__)` and inherit console + rotating file handlers.
A rotating file handler is used (rather than a single growing file) because
this app is meant to run continuously on a daily basis — logs must not grow
unbounded.
"""

import logging
import logging.handlers
import sys

from app.core.config import get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    settings = get_settings()
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.handlers.clear()  # avoid duplicate handlers on reload

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_DIR / "kalastree_pulse.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Uvicorn's access logger is noisy at INFO level; keep it quieter unless debugging.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
