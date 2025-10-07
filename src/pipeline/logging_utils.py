"""Utility helpers for consistent pipeline logging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union


_INITIALIZED = False


def setup_pipeline_logging(
    log_file: Union[str, Path] = "logs/pipeline.log",
    level: int = logging.INFO,
) -> None:
    """Configure a shared logger for pipeline commands.

    The configuration is idempotent so repeated calls will not add duplicate
    handlers. Logs are sent both to stdout (for CLI visibility) and to a
    rolling file inside ``logs/`` for later diagnostics.
    """

    global _INITIALIZED
    if _INITIALIZED:
        return

    logger = logging.getLogger("pipeline")
    if logger.handlers:
        _INITIALIZED = True
        return

    logger.setLevel(level)
    logger.propagate = False

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _INITIALIZED = True


def get_pipeline_logger(name: str) -> logging.Logger:
    """Return a child logger below the common ``pipeline`` namespace."""

    if not name.startswith("pipeline"):
        name = f"pipeline.{name}"
    return logging.getLogger(name)

