"""
System management and batch operations endpoints.

Provides centralized control for all background tasks and system operations.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.translation_job import TranslationJob
from app.models.user import User
from app.workers.celery_app import celery_app
from app.workers.tasks import asr_then_translate_task, scan_library_task, translate_subtitle_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system", tags=["System Management"])


# === Request/Response Schemas ===


class BatchOperationRequest(BaseModel):
    """Request for batch operations on jobs."""

    job_ids: list[UUID] = []
    status_filter: str | None = None  # Filter by status: queued, running, failed, completed


class BatchOperationResponse(BaseModel):
    """Response for batch operations."""

    success: bool
    affected_count: int
    message: str


class ScanAllLibrariesRequest(BaseModel):
    """Request to scan all Jellyfin libraries."""

    force_rescan: bool = False
    required_langs: list[str] | None = None


class ScanAllLibrariesResponse(BaseModel):
    """Response for scan all libraries operation."""

    task_id: str
    message: str


class QueueStatsResponse(BaseModel):
    """Celery queue statistics."""

    translate_queue: int
    asr_queue: int
    scan_queue: int
    total: int


class WorkerStatsResponse(BaseModel):
    """Celery worker statistics."""

    active_workers: int
    workers: list[dict]


class SystemStatsResponse(BaseModel):
    """System statistics."""

    total_jobs: int
    queued_jobs: int
    running_jobs: int
    paused_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int


# === Batch Operations ===


@router.post("/batch/start-all-queued", response_model=BatchOperationResponse)
async def batch_start_all_queued(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchOperationResponse:
    """
    Start all queued translation jobs.

    Returns:
        BatchOperationResponse with count of started jobs
    """
    try:
        # Get all queued jobs
        queued_jobs = db.query(TranslationJob).filter(TranslationJob.status == "queued").all()

        started_count = 0
        for job in queued_jobs:
            try:
                # Dispatch to appropriate queue based on source type
                if job.source_type == "subtitle":
                    task = translate_subtitle_task.apply_async(
                        args=[str(job.id)],
                        queue="translate",
                    )
                elif job.source_type in ("audio", "media", "jellyfin"):
                    task = asr_then_translate_task.apply_async(
                        args=[str(job.id)],
                        queue="asr",
                    )
                else:
                    logger.warning(f"Unknown source type for job {job.id}: {job.source_type}")
                    continue

                # Update job with task ID
                job.celery_task_id = task.id
                job.status = "running"
                started_count += 1

            except Exception as e:
                logger.error(f"Failed to start job {job.id}: {e}")
                continue

        db.commit()

        logger.info(f"Batch started {started_count} queued jobs")
        return BatchOperationResponse(
            success=True,
            affected_count=started_count,
            message=f"Successfully started {started_count} queued jobs",
        )

    except Exception as e:
        logger.error(f"Batch start all queued failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/cancel-all-running", response_model=BatchOperationResponse)
async def batch_cancel_all_running(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchOperationResponse:
    """
    Cancel all running and queued translation jobs.

    Returns:
        BatchOperationResponse with count of cancelled jobs
    """
    try:
        # Get all running and queued jobs
        jobs = (
            db.query(TranslationJob).filter(TranslationJob.status.in_(["queued", "running"])).all()
        )

        cancelled_count = 0
        for job in jobs:
            try:
                # Revoke Celery task if exists
                if job.celery_task_id:
                    celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGKILL")

                # Update job status
                job.status = "cancelled"
                cancelled_count += 1

            except Exception as e:
                logger.error(f"Failed to cancel job {job.id}: {e}")
                continue

        db.commit()

        logger.info(f"Batch cancelled {cancelled_count} jobs")
        return BatchOperationResponse(
            success=True,
            affected_count=cancelled_count,
            message=f"Successfully cancelled {cancelled_count} jobs",
        )

    except Exception as e:
        logger.error(f"Batch cancel all running failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/delete-completed", response_model=BatchOperationResponse)
async def batch_delete_completed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchOperationResponse:
    """
    Delete all completed, failed, and cancelled jobs.

    Returns:
        BatchOperationResponse with count of deleted jobs
    """
    try:
        # Delete jobs with final status
        deleted_count = (
            db.query(TranslationJob)
            .filter(TranslationJob.status.in_(["completed", "failed", "cancelled"]))
            .delete(synchronize_session=False)
        )

        db.commit()

        logger.info(f"Batch deleted {deleted_count} completed jobs")
        return BatchOperationResponse(
            success=True,
            affected_count=deleted_count,
            message=f"Successfully deleted {deleted_count} completed jobs",
        )

    except Exception as e:
        logger.error(f"Batch delete completed failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# === Library Scanning ===


@router.post("/scan/all-libraries", response_model=ScanAllLibrariesResponse)
async def scan_all_libraries(
    request: ScanAllLibrariesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanAllLibrariesResponse:
    """
    Scan all Jellyfin libraries for missing subtitles.

    Args:
        request: Scan configuration

    Returns:
        Task ID for the scan operation
    """
    try:
        # Get required languages
        # 如果请求中提供了语言列表则使用，否则从自动翻译规则推断
        if request.required_langs:
            required_langs = request.required_langs
        else:
            from app.services.detector import get_required_langs_from_rules

            required_langs = get_required_langs_from_rules(db)

        # Submit scan task
        task = scan_library_task.apply_async(
            kwargs={
                "library_id": None,  # None means scan all
                "required_langs": required_langs,
                "force_rescan": request.force_rescan,
            },
            queue="scan",
            priority=3,
        )

        logger.info(f"Scan all libraries task created: {task.id}")

        return ScanAllLibrariesResponse(
            task_id=str(task.id),
            message=f"Scan task queued for all libraries with languages: {', '.join(required_langs)}",
        )

    except Exception as e:
        logger.error(f"Failed to scan all libraries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === System Statistics ===


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemStatsResponse:
    """
    Get system statistics.

    Returns:
        System statistics including job counts by status
    """
    try:
        stats = {
            "total_jobs": db.query(TranslationJob).count(),
            "queued_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "queued")
            .count(),
            "running_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "running")
            .count(),
            "paused_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "paused")
            .count(),
            "completed_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "completed")
            .count(),
            "failed_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "failed")
            .count(),
            "cancelled_jobs": db.query(TranslationJob)
            .filter(TranslationJob.status == "cancelled")
            .count(),
        }

        return SystemStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get system stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue-stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
) -> QueueStatsResponse:
    """
    Get Celery queue statistics.

    Returns:
        Queue statistics for all queues
    """
    try:
        # Get queue lengths using Celery inspect
        inspect = celery_app.control.inspect()

        # Get reserved (active) tasks
        reserved = inspect.reserved()
        active = inspect.active()

        # Count tasks in each queue
        translate_count = 0
        asr_count = 0
        scan_count = 0

        if reserved:
            for _worker, tasks in reserved.items():
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "")
                    if "translate" in queue:
                        translate_count += 1
                    elif "asr" in queue:
                        asr_count += 1
                    elif "scan" in queue:
                        scan_count += 1

        if active:
            for _worker, tasks in active.items():
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "")
                    if "translate" in queue:
                        translate_count += 1
                    elif "asr" in queue:
                        asr_count += 1
                    elif "scan" in queue:
                        scan_count += 1

        return QueueStatsResponse(
            translate_queue=translate_count,
            asr_queue=asr_count,
            scan_queue=scan_count,
            total=translate_count + asr_count + scan_count,
        )

    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}", exc_info=True)
        # Return zeros on error
        return QueueStatsResponse(translate_queue=0, asr_queue=0, scan_queue=0, total=0)


@router.get("/worker-stats", response_model=WorkerStatsResponse)
async def get_worker_stats(
    current_user: User = Depends(get_current_user),
) -> WorkerStatsResponse:
    """
    Get Celery worker statistics.

    Returns:
        Worker statistics including active worker count
    """
    try:
        # Get worker stats using Celery inspect
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        workers = []
        if stats:
            for worker_name, worker_stats in stats.items():
                workers.append(
                    {
                        "name": worker_name,
                        "total_tasks": worker_stats.get("total", {}),
                        "pool": worker_stats.get("pool", {}),
                    }
                )

        return WorkerStatsResponse(active_workers=len(workers), workers=workers)

    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}", exc_info=True)
        return WorkerStatsResponse(active_workers=0, workers=[])
