"""
Structured logging configuration for FluxCaption.

Provides JSON-formatted logging with context tracking for jobs, phases, and operations.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

# =============================================================================
# Context Variables for Request/Task Tracking
# =============================================================================

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)
phase_var: ContextVar[str | None] = ContextVar("phase", default=None)


# =============================================================================
# JSON Formatter
# =============================================================================


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs log records as JSON objects with timestamp, level, message,
    and additional context fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context variables if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        job_id = job_id_var.get()
        if job_id:
            log_data["job_id"] = job_id

        phase = phase_var.get()
        if phase:
            log_data["phase"] = phase

        # Add extra fields from the record
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add stack trace if present
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        # Add module and function information
        log_data["module"] = record.module
        log_data["function"] = record.funcName
        log_data["line"] = record.lineno

        return json.dumps(log_data)


# =============================================================================
# Text Formatter (for human-readable output)
# =============================================================================


class TextFormatter(logging.Formatter):
    """
    Custom text formatter for human-readable logging.

    Provides colored output and structured information.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a colored text string."""
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Build context string
        context_parts = []
        job_id = job_id_var.get()
        if job_id:
            context_parts.append(f"job={job_id[:8]}")

        phase = phase_var.get()
        if phase:
            context_parts.append(f"phase={phase}")

        context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

        # Format the message
        message = (
            f"{color}{timestamp} {record.levelname:8s}{self.RESET} "
            f"{record.name}{context_str}: {record.getMessage()}"
        )

        # Add exception information if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


# =============================================================================
# Logger Configuration
# =============================================================================


def configure_logging() -> None:
    """
    Configure application logging based on settings.

    Sets up formatters, handlers, and log levels according to configuration.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on configuration
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure stdout handler
    if settings.log_output in ("stdout", "both"):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(getattr(logging, settings.log_level))
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

    # Configure file handler
    if settings.log_output in ("file", "both"):
        # Ensure log directory exists
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setLevel(getattr(logging, settings.log_level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific logger levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


# =============================================================================
# Logger Helper Functions
# =============================================================================


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: The logger name (typically __name__)

    Returns:
        logging.Logger: A configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **extra: Any) -> None:
    """
    Log a message with additional context fields.

    Args:
        logger: The logger instance
        level: The log level (e.g., logging.INFO)
        message: The log message
        **extra: Additional context fields to include
    """
    logger.log(level, message, extra=extra)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.

    Args:
        request_id: The request ID to set
    """
    request_id_var.set(request_id)


def set_job_id(job_id: str) -> None:
    """
    Set the job ID for the current context.

    Args:
        job_id: The job ID to set
    """
    job_id_var.set(job_id)


def set_phase(phase: str) -> None:
    """
    Set the phase for the current context.

    Args:
        phase: The phase name (e.g., 'pull', 'asr', 'mt', 'writeback')
    """
    phase_var.set(phase)


def clear_context() -> None:
    """Clear all context variables."""
    request_id_var.set(None)
    job_id_var.set(None)
    phase_var.set(None)


# =============================================================================
# Context Manager for Job Logging
# =============================================================================


class JobLogContext:
    """
    Context manager for job logging.

    Automatically sets and clears job_id and phase in the logging context.

    Example:
        with JobLogContext(job_id="abc123", phase="translate"):
            logger.info("Processing translation")
    """

    def __init__(self, job_id: str | None = None, phase: str | None = None):
        """
        Initialize the job log context.

        Args:
            job_id: Optional job ID to set
            phase: Optional phase name to set
        """
        self.job_id = job_id
        self.phase = phase
        self.previous_job_id = None
        self.previous_phase = None

    def __enter__(self) -> "JobLogContext":
        """Enter the context and set logging variables."""
        if self.job_id:
            self.previous_job_id = job_id_var.get()
            set_job_id(self.job_id)

        if self.phase:
            self.previous_phase = phase_var.get()
            set_phase(self.phase)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and restore previous logging variables."""
        if self.job_id:
            if self.previous_job_id:
                set_job_id(self.previous_job_id)
            else:
                job_id_var.set(None)

        if self.phase:
            if self.previous_phase:
                set_phase(self.previous_phase)
            else:
                phase_var.set(None)


# =============================================================================
# Initialize Logging on Module Import
# =============================================================================

configure_logging()
