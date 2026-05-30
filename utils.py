"""
Shared utilities: logging configuration, directory helpers, label normalisation.
"""

import logging
import os
from datetime import datetime

import config as cfg


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger: console + timestamped log file (never overwritten)."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"

    log_dir = os.path.join(cfg.SCRIPT_DIR, "output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(log_dir, f"run_{timestamp}.log")

    logging.basicConfig(format=fmt, level=level, datefmt="%H:%M:%S")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%H:%M:%S"))
    file_handler.setLevel(level)
    logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger("fork_pipeline")
    logger.info("Log file: %s", log_path)
    return logger


def ensure_output_dirs() -> None:
    """Create ``output/figures/`` if it does not already exist."""
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)


def normalize_hand_label(raw: str) -> str:
    """Normalise a tremor-hand label to ``Right`` / ``Left`` / ``Bilateral``.

    Handles English values and common Hebrew equivalents.

    Args:
        raw: Raw string from the CRF cell.

    Returns:
        One of ``"Right"``, ``"Left"``, ``"Bilateral"``, or ``"Unknown"``.
    """
    if not isinstance(raw, str):
        return "Unknown"
    cleaned = raw.strip()
    mapping = {
        "right": "Right",
        "left": "Left",
        "bilateral": "Bilateral",
        "ימין": "Right",
        "שמאל": "Left",
    }
    return mapping.get(cleaned.lower(), "Unknown")
