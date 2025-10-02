"""
Celery application configuration.

Configures Celery for distributed task processing.
"""

from celery import Celery
from celery.signals import setup_logging

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


# =============================================================================
# Celery Application
# =============================================================================

celery_app = Celery(
    "fluxcaption",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)


# =============================================================================
# Celery Configuration
# =============================================================================

celery_app.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=settings.celery_task_track_started,
    task_send_sent_event=True,

    # Task time limits
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_time_limit - 60,

    # Task retry behavior
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker configuration
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_disable_rate_limits=False,

    # Result backend
    result_expires=86400,  # 24 hours
    result_persistent=True,

    # Broker connection
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Task routes
    task_routes={
        "app.workers.tasks.scan_library_task": {"queue": "scan"},
        "app.workers.tasks.translate_subtitle_task": {"queue": "translate"},
        "app.workers.tasks.asr_then_translate_task": {"queue": "asr"},
    },

    # Task rate limits (tasks per second)
    task_annotations={
        "app.workers.tasks.scan_library_task": {
            "rate_limit": f"{settings.max_concurrent_scan_tasks}/s"
        },
        "app.workers.tasks.translate_subtitle_task": {
            "rate_limit": f"{settings.max_concurrent_translate_tasks}/s"
        },
        "app.workers.tasks.asr_then_translate_task": {
            "rate_limit": f"{settings.max_concurrent_asr_tasks}/s"
        },
    },

    # Beat schedule (for periodic tasks)
    beat_schedule={
        # Example: periodic library scan
        # "scan-libraries": {
        #     "task": "app.workers.tasks.scan_library_task",
        #     "schedule": 3600.0,  # Every hour
        # },
    },
)


# =============================================================================
# Logging Configuration
# =============================================================================

@setup_logging.connect
def setup_celery_logging(**kwargs):
    """
    Configure logging for Celery.

    This overrides Celery's default logging configuration to use our
    structured logging setup.
    """
    configure_logging()
    logger.info("Celery logging configured")


# =============================================================================
# Task Discovery
# =============================================================================

celery_app.autodiscover_tasks(["app.workers"])


# =============================================================================
# Debug Info
# =============================================================================

if __name__ == "__main__":
    logger.info("Celery configuration:")
    logger.info(f"  Broker: {settings.celery_broker_url}")
    logger.info(f"  Backend: {settings.celery_result_backend}")
    logger.info(f"  Max tasks per child: {settings.celery_worker_max_tasks_per_child}")
    logger.info(f"  Prefetch multiplier: {settings.celery_worker_prefetch_multiplier}")
