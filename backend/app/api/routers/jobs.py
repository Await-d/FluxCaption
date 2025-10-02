"""
Job management endpoints.

Provides API for creating, querying, and monitoring translation jobs.
"""

import json
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.db import get_db
from app.core.events import generate_sse_response
from app.core.config import settings
from app.core.logging import get_logger
from app.models.translation_job import TranslationJob
from app.schemas.jobs import JobCreate, JobResponse, JobListResponse
from app.workers.tasks import translate_subtitle_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post(
    "/translate",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create translation job",
)
async def create_translation_job(
    request: JobCreate,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Create a new translation job.

    Args:
        request: Job creation request
        db: Database session

    Returns:
        JobResponse: Created job information

    Raises:
        HTTPException: If job creation fails
    """
    try:
        # Determine model to use
        model = request.model or settings.default_mt_model

        # Create job record
        job = TranslationJob(
            item_id=request.item_id,
            source_type=request.source_type,
            source_path=request.source_path,
            source_lang=request.source_lang,
            target_langs=json.dumps(request.target_langs),
            model=model,
            status="queued",
            progress=0.0,
            writeback_mode=request.writeback_mode,
            priority=request.priority,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Created translation job: {job.id}")

        # Submit to Celery based on source type
        if request.source_type == "subtitle":
            # Direct subtitle translation
            task = translate_subtitle_task.apply_async(
                args=[str(job.id)],
                queue="translate",
                priority=request.priority,
            )
        elif request.source_type in ("audio", "media"):
            # ASR + translation pipeline
            from app.workers.tasks import asr_then_translate_task

            task = asr_then_translate_task.apply_async(
                args=[str(job.id)],
                queue="asr",
                priority=request.priority,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source_type: {request.source_type}",
            )

        # Update job with Celery task ID
        job.celery_task_id = task.id
        db.commit()

        return JobResponse(
            id=job.id,
            item_id=job.item_id,
            source_type=job.source_type,
            source_path=job.source_path,
            source_lang=job.source_lang,
            target_langs=json.loads(job.target_langs),
            model=job.model,
            status=job.status,
            progress=job.progress,
            current_phase=job.current_phase,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            result_paths=json.loads(job.result_paths) if job.result_paths else None,
            metrics=json.loads(job.metrics) if job.metrics else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create translation job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}",
        )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Get detailed job information.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        JobResponse: Job information

    Raises:
        HTTPException: If job not found
    """
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    return JobResponse(
        id=job.id,
        item_id=job.item_id,
        source_type=job.source_type,
        source_path=job.source_path,
        source_lang=job.source_lang,
        target_langs=json.loads(job.target_langs),
        model=job.model,
        status=job.status,
        progress=job.progress,
        current_phase=job.current_phase,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result_paths=json.loads(job.result_paths) if job.result_paths else None,
        metrics=json.loads(job.metrics) if job.metrics else None,
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
) -> JobListResponse:
    """
    List translation jobs with pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status_filter: Optional status filter
        db: Database session

    Returns:
        JobListResponse: Paginated list of jobs
    """
    # Build query
    query = db.query(TranslationJob)

    if status_filter:
        query = query.filter(TranslationJob.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    jobs = (
        query.order_by(desc(TranslationJob.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Convert to response models
    job_responses = [
        JobResponse(
            id=job.id,
            item_id=job.item_id,
            source_type=job.source_type,
            source_path=job.source_path,
            source_lang=job.source_lang,
            target_langs=json.loads(job.target_langs),
            model=job.model,
            status=job.status,
            progress=job.progress,
            current_phase=job.current_phase,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            result_paths=json.loads(job.result_paths) if job.result_paths else None,
            metrics=json.loads(job.metrics) if job.metrics else None,
        )
        for job in jobs
    ]

    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{job_id}/events",
    summary="Stream job progress",
    response_class=StreamingResponse,
)
async def stream_job_progress(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Stream job progress updates via Server-Sent Events (SSE).

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        StreamingResponse: SSE stream

    Raises:
        HTTPException: If job not found
    """
    # Verify job exists
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    # Return SSE stream
    channel = f"job:{job_id}"
    return StreamingResponse(
        generate_sse_response(channel),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )



@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel job",
)
async def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Cancel a running or queued translation job.

    Attempts to revoke the Celery task and mark the job as cancelled.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        JobResponse: Updated job information

    Raises:
        HTTPException: If job not found or cannot be cancelled
    """
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    # Check if job can be cancelled
    if job.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is already {job.status}, cannot cancel",
        )

    if job.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has already failed, use /retry to rerun it",
        )

    try:
        # Revoke Celery task if it exists
        if job.celery_task_id:
            from app.workers.celery_app import celery_app

            celery_app.control.revoke(
                job.celery_task_id,
                terminate=True,
                signal="SIGTERM",
            )
            logger.info(f"Revoked Celery task {job.celery_task_id} for job {job_id}")

        # Update job status
        job.status = "cancelled"
        job.error = "Job cancelled by user request"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        logger.info(f"Cancelled job: {job_id}")

        return JobResponse(
            id=job.id,
            item_id=job.item_id,
            source_type=job.source_type,
            source_path=job.source_path,
            source_lang=job.source_lang,
            target_langs=json.loads(job.target_langs),
            model=job.model,
            status=job.status,
            progress=job.progress,
            current_phase=job.current_phase,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            result_paths=json.loads(job.result_paths) if job.result_paths else None,
            metrics=json.loads(job.metrics) if job.metrics else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}",
        )


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Retry failed job",
)
async def retry_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Retry a failed or cancelled translation job.

    Creates a new job with the same parameters and submits it to the queue.

    Args:
        job_id: Original job ID
        db: Database session

    Returns:
        JobResponse: New job information

    Raises:
        HTTPException: If original job not found or cannot be retried
    """
    original_job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()

    if not original_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    # Check if job can be retried
    if original_job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is {original_job.status}, can only retry failed or cancelled jobs",
        )

    try:
        # Create new job with same parameters
        new_job = TranslationJob(
            item_id=original_job.item_id,
            source_type=original_job.source_type,
            source_path=original_job.source_path,
            source_lang=original_job.source_lang,
            target_langs=original_job.target_langs,
            model=original_job.model,
            status="queued",
            progress=0.0,
            writeback_mode=original_job.writeback_mode,
            priority=original_job.priority,
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        logger.info(f"Created retry job {new_job.id} for original job {job_id}")

        # Submit to Celery based on source type
        if original_job.source_type == "subtitle":
            task = translate_subtitle_task.apply_async(
                args=[str(new_job.id)],
                queue="translate",
                priority=original_job.priority or 5,
            )
        elif original_job.source_type in ("audio", "media"):
            # Import ASR task when it's ready
            from app.workers.tasks import asr_then_translate_task

            task = asr_then_translate_task.apply_async(
                args=[str(new_job.id)],
                queue="asr",
                priority=original_job.priority or 5,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source_type: {original_job.source_type}",
            )

        # Update job with Celery task ID
        new_job.celery_task_id = task.id
        db.commit()
        db.refresh(new_job)

        logger.info(f"Submitted retry job {new_job.id} with task ID {task.id}")

        return JobResponse(
            id=new_job.id,
            item_id=new_job.item_id,
            source_type=new_job.source_type,
            source_path=new_job.source_path,
            source_lang=new_job.source_lang,
            target_langs=json.loads(new_job.target_langs),
            model=new_job.model,
            status=new_job.status,
            progress=new_job.progress,
            current_phase=new_job.current_phase,
            error=new_job.error,
            created_at=new_job.created_at,
            started_at=new_job.started_at,
            finished_at=new_job.finished_at,
            result_paths=json.loads(new_job.result_paths) if new_job.result_paths else None,
            metrics=json.loads(new_job.metrics) if new_job.metrics else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}",
        )



@router.get(
    "/{job_id}/download/{file_index}",
    summary="Download translated subtitle",
)
async def download_subtitle(
    job_id: str,
    file_index: int,
    db: Session = Depends(get_db),
):
    """
    Download a translated subtitle file from a completed job.

    Args:
        job_id: Job ID
        file_index: Index in result_paths array (default: 0)
        db: Database session

    Returns:
        FileResponse: Subtitle file

    Raises:
        HTTPException: If job not found, not completed, or file doesn't exist
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    import os
    
    try:
        # Get job
        job = db.query(TranslationJob).filter(TranslationJob.id == UUID(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check job status
        if job.status != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed successfully. Status: {job.status}"
            )
        
        # Parse result_paths
        if not job.result_paths:
            raise HTTPException(status_code=404, detail="No result files available")
        
        result_paths = json.loads(job.result_paths)
        
        if file_index >= len(result_paths):
            raise HTTPException(
                status_code=404,
                detail=f"File index {file_index} out of range. Available: {len(result_paths)}"
            )
        
        file_path = result_paths[file_index]
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}"
            )
        
        # Get filename from path
        filename = Path(file_path).name
        
        logger.info(f"Downloading subtitle file: {file_path} for job {job_id}")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download subtitle for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download subtitle: {str(e)}"
        )



@router.get(
    "/{job_id}/preview/source",
    summary="Preview source subtitle",
)
async def preview_source_subtitle(
    job_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
    db: Session = Depends(get_db),
):
    """
    Preview the source subtitle of a translation job.

    Args:
        job_id: Job ID
        limit: Maximum number of subtitle entries to return (1-1000)
        offset: Number of entries to skip from beginning
        db: Database session

    Returns:
        Dictionary containing parsed subtitle entries

    Raises:
        HTTPException: If job not found or source file doesn't exist
    """
    from app.services.subtitle_parser import SubtitleParser
    
    try:
        # Get job
        job = db.query(TranslationJob).filter(TranslationJob.id == UUID(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check source_path
        if not job.source_path:
            raise HTTPException(status_code=404, detail="No source subtitle file available")
        
        logger.info(f"Previewing source subtitle for job {job_id}: {job.source_path}")
        
        # Parse subtitle file
        parser = SubtitleParser()
        result = parser.parse(job.source_path, limit=limit, offset=offset)
        
        return result
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Source subtitle file not found for job {job_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Source subtitle file not found: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Failed to parse source subtitle for job {job_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse subtitle: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to preview source subtitle for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview subtitle: {str(e)}"
        )


@router.get(
    "/{job_id}/preview/result/{file_index}",
    summary="Preview translated subtitle",
)
async def preview_result_subtitle(
    job_id: str,
    file_index: int,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
    db: Session = Depends(get_db),
):
    """
    Preview a translated subtitle from a completed job.

    Args:
        job_id: Job ID
        file_index: Index in result_paths array
        limit: Maximum number of subtitle entries to return (1-1000)
        offset: Number of entries to skip from beginning
        db: Database session

    Returns:
        Dictionary containing parsed subtitle entries

    Raises:
        HTTPException: If job not found, not completed, or file doesn't exist
    """
    from app.services.subtitle_parser import SubtitleParser
    
    try:
        # Get job
        job = db.query(TranslationJob).filter(TranslationJob.id == UUID(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check job status
        if job.status != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed successfully. Status: {job.status}"
            )
        
        # Parse result_paths
        if not job.result_paths:
            raise HTTPException(status_code=404, detail="No result files available")
        
        result_paths = json.loads(job.result_paths)
        
        if file_index >= len(result_paths):
            raise HTTPException(
                status_code=404,
                detail=f"File index {file_index} out of range. Available: {len(result_paths)}"
            )
        
        file_path = result_paths[file_index]
        
        logger.info(f"Previewing result subtitle for job {job_id}: {file_path}")
        
        # Parse subtitle file
        parser = SubtitleParser()
        result = parser.parse(file_path, limit=limit, offset=offset)
        
        return result
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Result subtitle file not found for job {job_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Result subtitle file not found: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Failed to parse result subtitle for job {job_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse subtitle: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to preview result subtitle for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview subtitle: {str(e)}"
        )


@router.patch(
    "/{job_id}/subtitle/{file_index}",
    summary="Update subtitle entries",
)
async def update_subtitle_entries(
    job_id: str,
    file_index: int,
    entries: dict[int, str],
    db: Session = Depends(get_db),
):
    """
    Update specific subtitle entries in a translated subtitle file.
    
    Args:
        job_id: Job ID
        file_index: Index of the result file to update
        entries: Dictionary mapping entry indices to new text
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If update fails
    """
    import pysubs2
    from pathlib import Path
    
    try:
        # Get job
        job = db.query(TranslationJob).filter(TranslationJob.id == UUID(job_id)).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check job status
        if job.status != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed successfully. Status: {job.status}"
            )
        
        # Parse result_paths
        if not job.result_paths:
            raise HTTPException(status_code=404, detail="No result files available")
        
        result_paths = json.loads(job.result_paths)
        
        if file_index >= len(result_paths):
            raise HTTPException(
                status_code=404,
                detail=f"File index {file_index} out of range. Available: {len(result_paths)}"
            )
        
        file_path = result_paths[file_index]
        
        # Check file exists
        if not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Subtitle file not found: {file_path}"
            )
        
        logger.info(f"Updating subtitle entries for job {job_id}, file {file_path}")
        logger.info(f"Updating {len(entries)} entries: {list(entries.keys())}")
        
        # Load subtitle file
        subs = pysubs2.load(file_path)
        
        # Update entries
        updated_count = 0
        for index, new_text in entries.items():
            # Convert 1-based index to 0-based
            idx = index - 1
            
            if 0 <= idx < len(subs):
                subs[idx].text = new_text
                updated_count += 1
            else:
                logger.warning(f"Invalid entry index: {index} (valid range: 1-{len(subs)})")
        
        # Save subtitle file
        subs.save(file_path)
        
        logger.info(f"Updated {updated_count} subtitle entries in {file_path}")
        
        return {
            "message": f"Successfully updated {updated_count} entries",
            "updated_count": updated_count,
            "total_entries": len(subs),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subtitle for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subtitle: {str(e)}"
        )
