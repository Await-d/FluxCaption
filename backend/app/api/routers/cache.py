"""
Translation cache management endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
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
async def get_cache_stats(db: Session = Depends(get_db)):
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
