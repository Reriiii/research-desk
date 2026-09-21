import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOGGER_NAME = "research_agent"
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "research-agent.log"


def configure_logging(*, console: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    if not any(getattr(handler, "_research_file", False) for handler in logger.handlers):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler._research_file = True
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if console and not any(
        getattr(handler, "_research_console", False) for handler in logger.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler._research_console = True
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    for handler in logger.handlers:
        handler.setLevel(level)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def preview(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def log_model_response(
    logger: logging.Logger,
    *,
    operation: str,
    response: Any,
    duration_ms: float,
    run_id: str,
) -> None:
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = getattr(response, "usage_metadata", None) or metadata.get(
        "token_usage", {}
    )
    logger.info(
        "run_id=%s event=model_response operation=%s duration_ms=%.1f "
        "model=%s request_id=%s input_tokens=%s output_tokens=%s total_tokens=%s",
        run_id,
        operation,
        duration_ms,
        metadata.get("model_name") or metadata.get("model") or "unknown",
        metadata.get("id") or getattr(response, "id", None) or "unknown",
        usage.get("input_tokens") or usage.get("prompt_tokens") or 0,
        usage.get("output_tokens") or usage.get("completion_tokens") or 0,
        usage.get("total_tokens") or 0,
    )
