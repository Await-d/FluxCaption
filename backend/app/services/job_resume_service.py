"""
Paused job resume helpers.

Keeps manual resume and scheduled resume aligned on the same state reset and
redispatch logic.
"""

from datetime import datetime

from app.core.db import session_scope
from app.core.logging import get_logger
from app.models.translation_job import TranslationJob
from app.services.job_dispatcher import dispatch_translation_job

logger = get_logger(__name__)


def reset_paused_job_for_resume(job: TranslationJob) -> None:
    job.status = "queued"
    job.pause_reason = None
    job.paused_at = None
    job.resume_at = None
    job.error = None
    job.started_at = None


def resume_paused_job(job_id: str, *, priority: int | None = None) -> str:
    with session_scope() as session:
        job = (
            session.query(TranslationJob)
            .filter(TranslationJob.id == job_id)
            .with_for_update()
            .first()
        )

        if not job:
            raise ValueError(f"Job '{job_id}' not found")

        if job.status != "paused":
            raise ValueError(f"Job is {job.status}, can only resume paused jobs")

        reset_paused_job_for_resume(job)
        session.commit()
        session.refresh(job)

        task_id = dispatch_translation_job(job, priority=priority if priority is not None else job.priority)
        job.celery_task_id = task_id
        session.commit()

        logger.info(f"Resumed paused job {job_id} as Celery task {task_id}")
        return task_id


def resume_due_paused_jobs(now: datetime) -> dict:
    results = {"paused_jobs_found": 0, "jobs_resumed": 0, "jobs_still_paused": 0, "errors": []}

    with session_scope() as session:
        paused_jobs = (
            session.query(TranslationJob)
            .filter(
                TranslationJob.status == "paused",
                TranslationJob.resume_at.isnot(None),
                TranslationJob.resume_at <= now,
            )
            .all()
        )

        results["paused_jobs_found"] = len(paused_jobs)

        for job in paused_jobs:
            try:
                locked_job = (
                    session.query(TranslationJob)
                    .filter(TranslationJob.id == job.id)
                    .with_for_update(skip_locked=True)
                    .first()
                )

                if not locked_job or locked_job.status != "paused":
                    continue

                reset_paused_job_for_resume(locked_job)
                session.commit()
                session.refresh(locked_job)

                task_id = dispatch_translation_job(locked_job, priority=locked_job.priority)
                locked_job.celery_task_id = task_id
                session.commit()

                results["jobs_resumed"] += 1
                logger.info(f"Resubmitted job {locked_job.id} as Celery task {task_id}")

            except Exception as exc:
                session.rollback()
                results["errors"].append(f"Job {job.id}: {str(exc)}")

    return results
