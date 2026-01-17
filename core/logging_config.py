"""Centralized logging configuration.

Sets up Google Cloud Logging when available, with a sane console fallback.
"""
import logging
import os
from typing import Optional

_GCP_CONFIGURED = False


def init_logging(default_level="INFO"):
    """Initialize logging once for the app.

    - Attempts Google Cloud Logging if credentials are available.
    - Falls back to standard console logging.
    - Respects LOG_LEVEL env override.
    """
    global _GCP_CONFIGURED

    if getattr(init_logging, "_initialized", False): # Avoid re-initialization
        return

    level_name = os.getenv("LOG_LEVEL", default_level).upper() # Get log level from env
    level = getattr(logging, level_name, logging.INFO) # Default to INFO if invalid

    # Configure basic console logging first so we always have output.
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Try wiring Google Cloud Logging. If it fails, keep console logging.
    try:
        from google.cloud import logging as gcp_logging  # type: ignore

        client = gcp_logging.Client() # Automatically uses env credentials
        client.setup_logging(log_level=level) # Set GCP logging level
        _GCP_CONFIGURED = True
        logging.getLogger(__name__).info("Google Cloud Logging configured") # Log success
    except Exception as exc:  # noqa: BLE001 - initialization fallback
        logging.getLogger(__name__).warning(
            "Falling back to standard logging (GCP logging unavailable): %s", exc
        )

    init_logging._initialized = True


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Helper to get a named logger with optional level override."""
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger
