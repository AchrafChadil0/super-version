"""
Simple Production-Ready Logging
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Format logs as JSON"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": f"{record.filename}:{record.lineno}",
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields - they're stored directly on the record object
        # Standard LogRecord attributes to skip
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "getMessage",
            "taskName",
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class AppOnlyFilter(logging.Filter):
    """Filter that only allows logs from your application"""

    def __init__(self, app_prefixes):
        super().__init__()
        self.app_prefixes = app_prefixes

    def filter(self, record):
        # Allow logs that start with any of your app prefixes
        return any(record.name.startswith(prefix) for prefix in self.app_prefixes)


def setup_logging(log_level="INFO", log_dir="logs"):
    """
    Setup production logging with console and rotating file handlers
    Console: Shows ALL logs (including third-party)
    Files: Only YOUR application logs

    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_dir: Directory for log files
    """

    # Get the project root (assuming context_logger.py is in src/)
    project_root = Path(__file__).parent.parent
    log_path = project_root / log_dir

    # Create log directory
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture everything
    logger.handlers.clear()

    # Console handler - Shows EVERYTHING (no filter)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    # No filter on console - shows all logs
    logger.addHandler(console)

    # Create filter for your app logs only
    # Adjust these prefixes to match your logger names
    app_filter = AppOnlyFilter(
        [
            "src.",  # All loggers starting with "src."
            "__main__",  # Main script
            "__mp_main__",  # Multiprocessing main
        ]
    )

    # File handler - JSON format, rotating - ONLY YOUR APP LOGS
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "app.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JSONFormatter())
    file_handler.addFilter(app_filter)  # Add filter here
    logger.addHandler(file_handler)

    # Error file handler - ONLY YOUR APP ERRORS
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(app_filter)  # Add filter here
    logger.addHandler(error_handler)

    return logger

