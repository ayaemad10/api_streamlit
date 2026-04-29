"""
utils/logger.py
---------------
Centralized structured logging with file rotation and console output.
Used across API, dashboard, and all modules.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Returns a configured logger with:
      - Rotating file handler (10 MB, 5 backups)
      - Coloured console handler
      - Structured format: [TIME] [LEVEL] [MODULE] message

    Args:
        name:  Logger name (usually __name__).
        level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR').

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers when called multiple times
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── File handler (rotating) ──────────────────────────────────────
    log_file = LOG_DIR / f"{name.replace('.', '_')}.log"
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    fh.setLevel(numeric_level)
    logger.addHandler(fh)

    # ── Combined app log ─────────────────────────────────────────────
    app_fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=20 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    app_fh.setFormatter(fmt)
    app_fh.setLevel(numeric_level)
    logger.addHandler(app_fh)

    # ── Console handler (coloured) ───────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(_ColourFormatter())
    ch.setLevel(numeric_level)
    logger.addHandler(ch)

    logger.propagate = False
    return logger


class _ColourFormatter(logging.Formatter):
    """Adds ANSI colour codes to log levels for terminal output."""

    COLOURS = {
        logging.DEBUG:    "\033[36m",    # Cyan
        logging.INFO:     "\033[32m",    # Green
        logging.WARNING:  "\033[33m",    # Yellow
        logging.ERROR:    "\033[31m",    # Red
        logging.CRITICAL: "\033[35m",    # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelno, self.RESET)
        record.levelname = f"{colour}{record.levelname:<8}{self.RESET}"
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return fmt.format(record)
