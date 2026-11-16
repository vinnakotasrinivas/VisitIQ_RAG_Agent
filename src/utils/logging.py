"""Console + rotating file logging."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.config import LOG_DIR

_CONFIGURED = False


def get_logger(name: str = "visitiq") -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger("visitiq")
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
        file_handler = RotatingFileHandler(LOG_DIR / "visitiq.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        file_handler.setFormatter(fmt)
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console.setLevel(logging.WARNING)
        root.addHandler(file_handler)
        root.addHandler(console)
        root.propagate = False
        _CONFIGURED = True
    if name == "visitiq" or name.startswith("visitiq."):
        return logging.getLogger(name)
    return logging.getLogger(f"visitiq.{name}")
