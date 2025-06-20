# app/logging_config.py

"""
Configures structured JSON logging for the SimonGPT LLM Router service.

This module sets up the root logger using a StreamHandler that outputs
one JSON-formatted log line per event. This is optimized for use in:
- Dockerized environments
- Cloud logging systems (e.g., CloudWatch, GCP Logging, ELK)
- Distributed tracing tools

Uses the `python-json-logger` package to serialize logs to structured JSON.

💡 You can control log verbosity via the LOG_LEVEL environment variable (e.g., DEBUG, INFO, WARNING).
"""

import logging
import sys
from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str = "INFO") -> None:
    """
    Configures the global Python logger.

    This replaces any existing handlers with a single JSON formatter
    that outputs to stdout (typically consumed by Docker log drivers or cloud platforms).

    Args:
        level (str): Log level (e.g., "DEBUG", "INFO", "ERROR").
    """
    handler = logging.StreamHandler(sys.stdout)

    # JSON fields included in logs
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"

    # Structured JSON logging for observability
    handler.setFormatter(JsonFormatter(fmt))

    # Set up the root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
