"""
Subtitle Sync API Router

Endpoints for syncing subtitle files to translation memory.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.logging import get_logger
from app.models.subtitle import Subtitle
from app.models.subtitle_sync_record import SubtitleSyncRecord
from app.models.media_asset import MediaAsset
from app.services.subtitle_sync_service import SubtitleSyncService
from app.workers.tasks import (
    sync_subtitle_task,
    sync_asset_subtitles_task,
    sync_all_subtitles_task
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/subtitle-sync", tags=["subtitle-sync"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SyncSubtitleRequest(BaseModel):
    """Request to sync a single subtitle."""
    subtitle_id: str = Field(..., description="Subtitle ID to sync")
    mode: str = Field(
        "incremental",
        description="Sync mode: full, incremental, skip"
    )
    paired_subtitle_id: Optional[str] = Field(
        None,
        description="Optional paired subtitle ID for translation pairs"
    )


class SyncAssetRequest(BaseModel):
    """Request to sync all subtitles for an asset."""
    asset_id: str = Field(..., description="Media asset ID")
    mode: str = Field(
        "incremental",
        description="Sync mode: full, incremental, skip"
    )
    auto_pair: bool = Field(
        True,
        description="Automatically pair subtitles for translation memory"
    )


class BatchSyncRequest(BaseModel):
    """Request to batch sync multiple subtitles."""
    subtitle_ids: Optional[List[str]] = Field(
        None,
        description="List of subtitle IDs to sync (if None, sync all)"
    )
    mode: str = Field(
        "incremental",
        description="Sync mode: full, incremental, skip"
    )
    auto_pair: bool = Field(
        True,
        description="Auto-pair subtitles"
    )
    limit: Optional[int] = Field(
        None,
        description="Limit number of assets to process"
    )


class SyncRecordResponse(BaseModel):
    """Sync record response."""
    id: str
    subtitle_id: str
    asset_id: Optional[str]
    status: str
    sync_mode: str
    total_lines: int
    synced_lines: int
    skipped_lines: int
    failed_lines: int
    paired_subtitle_id: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    error_message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class SubtitlePairResponse(BaseModel):
    """Subtitle pair response."""
    source_subtitle_id: str
    source_lang: str
    target_subtitle_id: str
    target_lang: str


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    subtitle_id: str
    lang: str
    latest_sync: Optional[SyncRecordResponse]
    sync_count: int


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/sync", response_model=dict)
async def sync_subtitle(
    request: SyncSubtitleRequest,
    background: bool = Query(True, description="Run sync in background"),
    db: Session = Depends(get_db)
):
    """
    Sync a subtitle file to translation memory.

    Args:
        request: Sync request
        background: Whether to run in background (default: True)
        db: Database session

    Returns:
        Sync result or task ID
    """
    logger.info(f"Sync subtitle request: {request.subtitle_id}")

    # Verify subtitle exists
    subtitle = db.get(Subtitle, UUID(request.subtitle_id))
    if not subtitle:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    # Verify paired subtitle if provided
    if request.paired_subtitle_id:
        paired_subtitle = db.get(Subtitle, UUID(request.paired_subtitle_id))
        if not paired_subtitle:
            raise HTTPException(status_code=404, detail="Paired subtitle not found")

    if background:
        # Run in background using Celery
        task = sync_subtitle_task.apply_async(
            args=[request.subtitle_id],
            kwargs={
                "mode": request.mode,
                "paired_subtitle_id": request.paired_subtitle_id
            },
            queue="translate"
        )

        return {
            "status": "queued",
            "task_id": task.id,
            "subtitle_id": request.subtitle_id
        }
    else:
        # Run synchronously
        sync_service = SubtitleSyncService(db)
        sync_record = sync_service.sync_subtitle_to_memory(
            subtitle_id=request.subtitle_id,
            mode=request.mode,
            paired_subtitle_id=request.paired_subtitle_id
        )

        return {
            "status": sync_record.status,
            "sync_record_id": str(sync_record.id),
            "synced_lines": sync_record.synced_lines,
            "skipped_lines": sync_record.skipped_lines,
            "failed_lines": sync_record.failed_lines
        }


@router.post("/sync/asset", response_model=dict)
async def sync_asset_subtitles(
    request: SyncAssetRequest,
    background: bool = Query(True, description="Run sync in background"),
    db: Session = Depends(get_db)
):
    """
    Sync all subtitles for a media asset.

    Args:
        request: Sync request
        background: Whether to run in background
        db: Database session

    Returns:
        Sync results or task ID
    """
    logger.info(f"Sync asset subtitles request: {request.asset_id}")

    # Verify asset exists
    asset = db.get(MediaAsset, UUID(request.asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if background:
        # Run in background
        task = sync_asset_subtitles_task.apply_async(
            args=[request.asset_id],
            kwargs={
                "mode": request.mode,
                "auto_pair": request.auto_pair
            },
            queue="translate"
        )

        return {
            "status": "queued",
            "task_id": task.id,
            "asset_id": request.asset_id
        }
    else:
        # Run synchronously
        sync_service = SubtitleSyncService(db)
        results = sync_service.sync_asset_subtitles(
            asset_id=request.asset_id,
            mode=request.mode,
            auto_pair=request.auto_pair
        )

        return results


@router.post("/sync/batch", response_model=dict)
async def batch_sync_subtitles(
    request: BatchSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Batch sync multiple subtitles or all subtitles in the system.

    This endpoint always runs in the background.

    Args:
        request: Batch sync request
        db: Database session

    Returns:
        Task information
    """
    logger.info("Batch sync subtitles request")

    # Run global sync task
    task = sync_all_subtitles_task.apply_async(
        kwargs={
            "mode": request.mode,
            "auto_pair": request.auto_pair,
            "limit": request.limit
        },
        queue="translate"
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Batch sync started"
    }


@router.get("/status/{subtitle_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    subtitle_id: str,
    db: Session = Depends(get_db)
):
    """
    Get sync status for a subtitle.

    Args:
        subtitle_id: Subtitle ID
        db: Database session

    Returns:
        Sync status information
    """
    # Verify subtitle exists
    subtitle = db.get(Subtitle, UUID(subtitle_id))
    if not subtitle:
        raise HTTPException(status_code=404, detail="Subtitle not found")

    # Get latest sync record
    sync_service = SubtitleSyncService(db)
    latest_sync = sync_service.get_sync_status(subtitle_id)

    # Count total syncs
    sync_count = db.query(SubtitleSyncRecord).filter(
        SubtitleSyncRecord.subtitle_id == UUID(subtitle_id)
    ).count()

    return SyncStatusResponse(
        subtitle_id=subtitle_id,
        lang=subtitle.lang,
        latest_sync=SyncRecordResponse.from_orm(latest_sync) if latest_sync else None,
        sync_count=sync_count
    )


@router.get("/pairs/{asset_id}", response_model=List[SubtitlePairResponse])
async def discover_subtitle_pairs(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """
    Discover all possible subtitle pairs for an asset.

    Args:
        asset_id: Media asset ID
        db: Database session

    Returns:
        List of subtitle pairs
    """
    # Verify asset exists
    asset = db.get(MediaAsset, UUID(asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    sync_service = SubtitleSyncService(db)
    pairs = sync_service.discover_subtitle_pairs(asset_id)

    return [
        SubtitlePairResponse(
            source_subtitle_id=str(source.id),
            source_lang=source.lang,
            target_subtitle_id=str(target.id),
            target_lang=target.lang
        )
        for source, target in pairs
    ]


@router.get("/records", response_model=List[SyncRecordResponse])
async def list_sync_records(
    subtitle_id: Optional[str] = Query(None, description="Filter by subtitle ID"),
    asset_id: Optional[str] = Query(None, description="Filter by asset ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    List sync records with optional filters.

    Args:
        subtitle_id: Optional subtitle ID filter
        asset_id: Optional asset ID filter
        status: Optional status filter
        limit: Number of records
        offset: Offset for pagination
        db: Database session

    Returns:
        List of sync records
    """
    query = db.query(SubtitleSyncRecord)

    # Apply filters
    if subtitle_id:
        query = query.filter(SubtitleSyncRecord.subtitle_id == UUID(subtitle_id))
    if asset_id:
        query = query.filter(SubtitleSyncRecord.asset_id == UUID(asset_id))
    if status:
        query = query.filter(SubtitleSyncRecord.status == status)

    # Order by created_at descending
    query = query.order_by(SubtitleSyncRecord.created_at.desc())

    # Pagination
    records = query.limit(limit).offset(offset).all()

    return [SyncRecordResponse.from_orm(record) for record in records]


@router.delete("/records/{record_id}")
async def delete_sync_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a sync record.

    Args:
        record_id: Sync record ID
        db: Database session

    Returns:
        Success message
    """
    record = db.get(SubtitleSyncRecord, UUID(record_id))
    if not record:
        raise HTTPException(status_code=404, detail="Sync record not found")

    db.delete(record)
    db.commit()

    return {"status": "success", "message": "Sync record deleted"}

