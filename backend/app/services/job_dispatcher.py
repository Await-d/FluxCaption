"""
Job dispatch helpers.

Centralizes Celery routing for translation jobs so start / retry / resume / batch
paths share the same source-type and priority behavior.
"""

from app.core.logging import get_logger
from app.models.translation_job import TranslationJob

logger = get_logger(__name__)


def dispatch_translation_job(job: TranslationJob, priority: int | None = None) -> str:
    from app.workers.tasks import asr_then_translate_task, translate_subtitle_task

    effective_priority = priority if priority is not None else (job.priority or 5)

    if job.source_type == "subtitle":
        task = translate_subtitle_task.apply_async(
            args=[str(job.id)],
            queue="translate",
            priority=effective_priority,
        )
    elif job.source_type in ("audio", "media", "jellyfin"):
        task = asr_then_translate_task.apply_async(
            args=[str(job.id)],
            queue="asr",
            priority=effective_priority,
        )
    else:
        raise ValueError(f"Invalid source_type: {job.source_type}")

    logger.info(
        f"Dispatched job {job.id} to queue with priority {effective_priority} (source_type={job.source_type})"
    )
    return str(task.id)
