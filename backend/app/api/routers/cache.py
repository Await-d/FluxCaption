"""
Translation cache management endpoints.
"""

from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.api.routers.auth import get_current_user
from app.core.logging import get_logger
from app.services.translation_cache_service import TranslationCacheService
from app.schemas.cache import (
    CacheStatsResponse,
    CacheListResponse,
    ClearOldEntriesRequest,
    ClearAllEntriesRequest,
    ClearEntriesResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
)
async def get_cache_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Get translation cache statistics.
    
    Returns:
        Cache statistics including total entries, hits, and hit rate
    """
    try:
        cache_service = TranslationCacheService(db)
        stats = cache_service.get_cache_stats()
        
        logger.info(f"Retrieved cache stats: {stats}")
        
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.get(
    "/entries",
    response_model=CacheListResponse,
    summary="Get cache entries",
)
async def get_cache_entries(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200, description="Number of entries to return"),
    offset: int = Query(default=0, ge=0, description="Number of entries to skip"),
    source_lang: str | None = Query(default=None, description="Filter by source language"),
    target_lang: str | None = Query(default=None, description="Filter by target language"),
    model: str | None = Query(default=None, description="Filter by model name"),
    search: str | None = Query(default=None, description="Search in text content"),
    sort_by: str = Query(default="last_used_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of cache entries with filtering and sorting.
    
    Args:
        limit: Maximum number of entries to return
        offset: Number of entries to skip
        source_lang: Filter by source language
        target_lang: Filter by target language
        model: Filter by model name
        search: Search text in source or translated text
        sort_by: Field to sort by (hit_count, created_at, last_used_at)
        sort_order: Sort order (asc, desc)
        db: Database session
        
    Returns:
        Paginated list of cache entries
    """
    try:
        cache_service = TranslationCacheService(db)
        result = cache_service.get_entries(
            limit=limit,
            offset=offset,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        logger.info(
            f"Retrieved {len(result['entries'])} cache entries "
            f"(total={result['total']}, offset={offset})"
        )
        
        return CacheListResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to get cache entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache entries: {str(e)}"
        )


@router.delete(
    "/old",
    response_model=ClearEntriesResponse,
    summary="Clear old unused cache entries",
)
async def clear_old_entries(
    request: ClearOldEntriesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Clear cache entries that haven't been used for a specified number of days
    and have zero hits.
    
    Args:
        request: Request with days parameter
        db: Database session
        
    Returns:
        Number of entries deleted
    """
    try:
        cache_service = TranslationCacheService(db)
        deleted_count = cache_service.clear_old_entries(days=request.days)
        
        logger.info(f"Cleared {deleted_count} old cache entries (older than {request.days} days)")
        
        return ClearEntriesResponse(
            deleted_count=deleted_count,
            message=f"Successfully deleted {deleted_count} unused entries older than {request.days} days"
        )
        
    except Exception as e:
        logger.error(f"Failed to clear old entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear old entries: {str(e)}"
        )


@router.delete(
    "/all",
    response_model=ClearEntriesResponse,
    summary="Clear all cache entries",
)
async def clear_all_entries(
    request: ClearAllEntriesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Clear all cache entries.
    
    **Warning**: This action cannot be undone!
    
    Args:
        request: Request with confirmation
        db: Database session
        
    Returns:
        Number of entries deleted
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set 'confirm' to true to delete all entries"
        )
    
    try:
        cache_service = TranslationCacheService(db)
        deleted_count = cache_service.clear_all_entries()
        
        logger.warning(f"Cleared ALL {deleted_count} cache entries")
        
        return ClearEntriesResponse(
            deleted_count=deleted_count,
            message=f"Successfully deleted all {deleted_count} cache entries"
        )
        
    except Exception as e:
        logger.error(f"Failed to clear all entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear all entries: {str(e)}"
        )


@router.post(
    "/cleanup-temp",
    summary="清理临时文件",
)
async def cleanup_temp_files(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    立即触发清理临时文件任务。
    
    清理超过24小时的临时文件，包括：
    - 失败/取消任务的媒体文件
    - ASR 提取的音频文件
    - 其他临时文件
    
    Returns:
        任务触发结果和预估清理信息
    """
    try:
        from app.workers.tasks import cleanup_temp_files as cleanup_task
        from pathlib import Path
        import os
        from datetime import datetime, timedelta
        
        # 先统计需要清理的文件信息
        temp_dir = Path("/tmp/fluxcaption")
        threshold_time = datetime.now() - timedelta(hours=24)
        
        files_to_clean = 0
        dirs_to_clean = 0
        space_to_free = 0
        orphaned_cleaned = 0
        
        if temp_dir.exists():
            # Get all existing job IDs from database
            from app.core.db import get_db
            from app.models.translation_job import TranslationJob
            import re
            
            with next(get_db()) as db:
                existing_job_ids = {
                    str(job.id) 
                    for job in db.query(TranslationJob.id).all()
                }
            
            # Pattern to extract job ID from directory name (e.g., asr_<job_id>)
            job_id_pattern = re.compile(r'^asr_([0-9a-f\-]{36})$')
            
            for item in temp_dir.iterdir():
                try:
                    if not (item.is_dir() or item.is_file()):
                        continue
                    
                    should_clean = False
                    is_orphaned = False
                    
                    # Check if this is an orphaned job directory
                    if item.is_dir():
                        match = job_id_pattern.match(item.name)
                        if match:
                            job_id = match.group(1)
                            if job_id not in existing_job_ids:
                                should_clean = True
                                is_orphaned = True
                    
                    # Check modification time
                    if not should_clean:
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < threshold_time:
                            should_clean = True
                    
                    if should_clean:
                        if item.is_dir():
                            dir_size = sum(
                                f.stat().st_size 
                                for f in item.rglob('*') 
                                if f.is_file()
                            )
                            space_to_free += dir_size
                            dirs_to_clean += 1
                            if is_orphaned:
                                orphaned_cleaned += 1
                        else:
                            space_to_free += item.stat().st_size
                            files_to_clean += 1
                except Exception:
                    continue
        
        # 触发清理任务（使用 scan 队列）
        task = cleanup_task.apply_async(queue='scan')
        
        logger.info(
            f"Cleanup task triggered: {task.id}, "
            f"estimated {dirs_to_clean} dirs, {files_to_clean} files, "
            f"{space_to_free / 1024 / 1024:.2f} MB to free"
        )
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "estimated": {
                "dirs_to_clean": dirs_to_clean,
                "files_to_clean": files_to_clean,
                "orphaned_cleaned": orphaned_cleaned,
                "space_to_free_mb": round(space_to_free / 1024 / 1024, 2),
            },
            "message": f"临时文件清理任务已触发，预计将清理 {dirs_to_clean} 个目录（{orphaned_cleaned} 个孤立）、{files_to_clean} 个文件，释放约 {round(space_to_free / 1024 / 1024, 2)} MB"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger cleanup task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger cleanup: {str(e)}"
        )


@router.get(
    "/temp-stats",
    summary="获取临时文件统计",
)
async def get_temp_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    获取临时文件目录的统计信息。
    
    计算可清理空间包括：
    1. 超过24小时的旧文件
    2. 孤立文件（对应的任务已被删除）
    
    Returns:
        临时文件统计信息
    """
    try:
        from pathlib import Path
        from datetime import datetime, timedelta
        import re
        
        temp_dir = Path("/tmp/fluxcaption")
        
        if not temp_dir.exists():
            return {
                "total_size_mb": 0,
                "total_files": 0,
                "total_dirs": 0,
                "old_files": 0,
                "old_dirs": 0,
                "old_size_mb": 0,
                "orphaned_dirs": 0,
                "orphaned_size_mb": 0,
                "cleanable_size_mb": 0,
            }
        
        # Get all existing job IDs from database
        from app.models.translation_job import TranslationJob
        existing_job_ids = {
            str(job.id) 
            for job in db.query(TranslationJob.id).all()
        }
        
        threshold_time = datetime.now() - timedelta(hours=24)
        
        total_size = 0
        total_files = 0
        total_dirs = 0
        old_files = 0
        old_dirs = 0
        old_size = 0
        orphaned_dirs = 0
        orphaned_size = 0
        
        # Pattern to extract job ID from directory name (e.g., asr_<job_id>)
        job_id_pattern = re.compile(r'^asr_([0-9a-f\-]{36})$')
        
        for item in temp_dir.iterdir():
            try:
                if not (item.is_dir() or item.is_file()):
                    continue
                
                is_orphaned = False
                
                # Check if this is an orphaned job directory
                if item.is_dir():
                    match = job_id_pattern.match(item.name)
                    if match:
                        job_id = match.group(1)
                        if job_id not in existing_job_ids:
                            is_orphaned = True
                
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                is_old = mtime < threshold_time
                
                if item.is_dir():
                    dir_size = sum(
                        f.stat().st_size 
                        for f in item.rglob('*') 
                        if f.is_file()
                    )
                    total_size += dir_size
                    total_dirs += 1
                    
                    if is_orphaned:
                        orphaned_size += dir_size
                        orphaned_dirs += 1
                    
                    if is_old:
                        old_size += dir_size
                        old_dirs += 1
                else:
                    file_size = item.stat().st_size
                    total_size += file_size
                    total_files += 1
                    
                    if is_old:
                        old_size += file_size
                        old_files += 1
                        
            except Exception:
                continue
        
        # Cleanable size = old files + orphaned files (avoid double counting)
        # Note: orphaned files might also be old, so we use max to avoid double counting
        cleanable_size = max(old_size, orphaned_size)
        
        return {
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_files": total_files,
            "total_dirs": total_dirs,
            "old_files": old_files,
            "old_dirs": old_dirs,
            "old_size_mb": round(old_size / 1024 / 1024, 2),
            "orphaned_dirs": orphaned_dirs,
            "orphaned_size_mb": round(orphaned_size / 1024 / 1024, 2),
            "cleanable_size_mb": round(cleanable_size / 1024 / 1024, 2),
            "threshold_hours": 24,
        }
        
    except Exception as e:
        logger.error(f"Failed to get temp stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get temp stats: {str(e)}"
        )
