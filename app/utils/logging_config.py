"""Privacy-conscious local application logging."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def default_log_path() -> Path:
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    return base / "DevSnapshot" / "logs" / "devsnapshot.log"


def configure_logging(log_path: Path | None = None) -> logging.Logger:
    """Configure a small rotating log containing events, paths, and errors only."""

    logger = logging.getLogger("devsnapshot")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    path = log_path or default_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger
