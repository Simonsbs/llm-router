import logging, sys
from pythonjsonlogger.json import JsonFormatter

def configure_logging(level: str = "INFO") -> None:
    """Configure root logger to emit one JSON line per event."""
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(JsonFormatter(fmt))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
