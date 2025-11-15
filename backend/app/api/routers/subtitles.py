"""
Subtitle library API endpoints.

Provides REST API for browsing and managing subtitle records in the database.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.media_asset import MediaAsset
from app.models.subtitle import Subtitle
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/subtitles", tags=["Subtitles"])


# =============================================================================
# Response Models
# =============================================================================


class SubtitleRecord(BaseModel):
    """Subtitle record with media information."""

    id: str
    lang: str
    format: str
    origin: str
    source_lang: str | None
    is_uploaded: bool
    line_count: int | None
    word_count: int | None
    created_at: str

    # Media asset info
    media_name: str | None
    media_type: str | None
    media_path: str | None
    item_id: str | None

    class Config:
        from_attributes = True


class SubtitleListResponse(BaseModel):
    """Response for subtitle list endpoint."""

    subtitles: list[SubtitleRecord]
    total: int
    limit: int
    offset: int


class SubtitleContentResponse(BaseModel):
    """Response for subtitle content endpoint."""

    content: str
    format: str
    lang: str
    line_count: int


class DeleteSubtitleRequest(BaseModel):
    """Request for deleting subtitles."""

    subtitle_ids: list[str]
    delete_files: bool = False  # Whether to delete physical files


class DeleteSubtitleResponse(BaseModel):
    """Response for subtitle deletion."""

    deleted_count: int
    failed_ids: list[str]
    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=SubtitleListResponse)
async def list_subtitles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    lang: str | None = Query(default=None, description="Filter by language"),
    origin: str | None = Query(
        default=None, description="Filter by origin (asr/mt/manual/jellyfin)"
    ),
    search: str | None = Query(default=None, description="Search media name"),
):
    """
    List all subtitle records with pagination and filters.

    Args:
        db: Database session
        limit: Max results per page
        offset: Pagination offset
        lang: Filter by language code
        origin: Filter by origin type
        search: Search in media name

    Returns:
        Paginated list of subtitle records with media info
    """
    try:
        # Build query with joins
        query = db.query(
            Subtitle,
            MediaAsset.name.label("media_name"),
            MediaAsset.type.label("media_type"),
            MediaAsset.path.label("media_path"),
            MediaAsset.item_id.label("item_id"),
        ).outerjoin(MediaAsset, Subtitle.asset_id == MediaAsset.id)

        # Apply filters
        if lang:
            query = query.filter(Subtitle.lang == lang)

        if origin:
            query = query.filter(Subtitle.origin == origin)

        if search:
            query = query.filter(MediaAsset.name.ilike(f"%{search}%"))

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        query = query.order_by(desc(Subtitle.created_at))
        query = query.limit(limit).offset(offset)

        # Execute query
        results = query.all()

        # Format response
        subtitles = []
        for subtitle, media_name, media_type, media_path, item_id in results:
            subtitles.append(
                SubtitleRecord(
                    id=str(subtitle.id),
                    lang=subtitle.lang,
                    format=subtitle.format,
                    origin=subtitle.origin,
                    source_lang=subtitle.source_lang,
                    is_uploaded=subtitle.is_uploaded,
                    line_count=subtitle.line_count,
                    word_count=subtitle.word_count,
                    created_at=subtitle.created_at.isoformat() if subtitle.created_at else "",
                    media_name=media_name,
                    media_type=media_type,
                    media_path=media_path,
                    item_id=item_id,
                )
            )

        return SubtitleListResponse(
            subtitles=subtitles,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list subtitles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{subtitle_id}/content", response_model=SubtitleContentResponse)
async def get_subtitle_content(
    subtitle_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    max_lines: int = Query(default=500, ge=1, le=2000, description="Maximum lines to return"),
):
    """
    Get subtitle file content.

    Args:
        subtitle_id: Subtitle record ID
        db: Database session
        max_lines: Maximum number of lines to return

    Returns:
        Subtitle content with metadata
    """
    try:
        # Get subtitle record
        subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()

        if not subtitle:
            raise HTTPException(status_code=404, detail="Subtitle not found")

        # Read subtitle file
        from pathlib import Path

        file_path = Path(subtitle.storage_path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Subtitle file not found on disk")

        # Read file content (with line limit)
        lines = []
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated at {max_lines} lines)")
                    break
                lines.append(line)

        content = "".join(lines)

        return SubtitleContentResponse(
            content=content,
            format=subtitle.format,
            lang=subtitle.lang,
            line_count=subtitle.line_count or len([l for l in content.split("\n") if l.strip()]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subtitle content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_subtitle_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Get subtitle library statistics.

    Returns:
        Statistics about subtitle records
    """
    try:
        # Total subtitles
        total = db.query(func.count(Subtitle.id)).scalar()

        # By language
        by_lang = (
            db.query(Subtitle.lang, func.count(Subtitle.id).label("count"))
            .group_by(Subtitle.lang)
            .all()
        )

        # By origin
        by_origin = (
            db.query(Subtitle.origin, func.count(Subtitle.id).label("count"))
            .group_by(Subtitle.origin)
            .all()
        )

        # Uploaded vs not uploaded
        uploaded = db.query(func.count(Subtitle.id)).filter(Subtitle.is_uploaded).scalar()
        not_uploaded = db.query(func.count(Subtitle.id)).filter(not Subtitle.is_uploaded).scalar()

        return {
            "total": total,
            "by_language": dict(by_lang),
            "by_origin": dict(by_origin),
            "uploaded": uploaded,
            "not_uploaded": not_uploaded,
        }

    except Exception as e:
        logger.error(f"Failed to get subtitle stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{subtitle_id}")
async def delete_subtitle(
    subtitle_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    delete_file: bool = Query(default=False, description="Delete physical file"),
):
    """
    Delete a single subtitle record.

    Args:
        subtitle_id: Subtitle record ID
        db: Database session
        delete_file: Whether to delete the physical file

    Returns:
        Success message
    """
    try:
        # Get subtitle record
        subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()

        if not subtitle:
            raise HTTPException(status_code=404, detail="Subtitle not found")

        # Delete physical file if requested
        if delete_file:
            from pathlib import Path

            file_path = Path(subtitle.storage_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Deleted subtitle file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete subtitle file {file_path}: {e}")

        # Delete database record
        db.delete(subtitle)
        db.commit()

        logger.info(f"Deleted subtitle record: {subtitle_id}")

        return {
            "message": "Subtitle deleted successfully",
            "subtitle_id": subtitle_id,
            "file_deleted": delete_file,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete subtitle: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch-delete", response_model=DeleteSubtitleResponse)
async def batch_delete_subtitles(
    request: DeleteSubtitleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Delete multiple subtitle records in batch.

    Args:
        request: Batch delete request with subtitle IDs
        db: Database session

    Returns:
        Deletion result with count and failed IDs
    """
    try:
        if not request.subtitle_ids:
            raise HTTPException(status_code=400, detail="No subtitle IDs provided")

        deleted_count = 0
        failed_ids = []

        for subtitle_id in request.subtitle_ids:
            try:
                # Get subtitle record
                subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()

                if not subtitle:
                    failed_ids.append(subtitle_id)
                    continue

                # Delete physical file if requested
                if request.delete_files:
                    from pathlib import Path

                    file_path = Path(subtitle.storage_path)
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            logger.info(f"Deleted subtitle file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete subtitle file {file_path}: {e}")

                # Delete database record
                db.delete(subtitle)
                deleted_count += 1

            except Exception as e:
                logger.error(f"Failed to delete subtitle {subtitle_id}: {e}")
                failed_ids.append(subtitle_id)

        # Commit all deletions
        db.commit()

        logger.info(f"Batch deleted {deleted_count} subtitles, {len(failed_ids)} failed")

        return DeleteSubtitleResponse(
            deleted_count=deleted_count,
            failed_ids=failed_ids,
            message=f"Successfully deleted {deleted_count} subtitle(s), {len(failed_ids)} failed",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch delete subtitles: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
