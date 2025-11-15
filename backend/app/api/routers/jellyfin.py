"""
Jellyfin integration API endpoints.

Provides REST API for:
- Listing Jellyfin libraries and items
- Triggering library scans
- Getting item details with language analysis
- Manual writeback operations
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_user
from app.core.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.jellyfin import (
    ItemDetailResponse,
    ItemListResponse,
    JellyfinItem,
    LibraryListResponse,
    ScanJobResponse,
    ScanLibraryRequest,
    WritebackRequest,
    WritebackResponse,
)
from app.services.detector import LanguageDetector
from app.services.jellyfin_client import (
    JellyfinError,
    JellyfinNotFoundError,
    get_jellyfin_client,
)
from app.services.writeback import WritebackError, WritebackService
from app.workers.tasks import scan_library_task

logger = get_logger(__name__)

router = APIRouter(prefix="/api/jellyfin", tags=["Jellyfin"])


# =============================================================================
# Library Endpoints
# =============================================================================


@router.get("/libraries", response_model=LibraryListResponse)
async def list_libraries(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    List all Jellyfin libraries.

    Returns:
        List of available libraries with metadata
    """
    try:
        jellyfin_client = get_jellyfin_client()
        libraries = await jellyfin_client.list_libraries()

        # Add image URLs for libraries that have Primary images
        for library in libraries:
            # Only generate image URL if library has a Primary image tag
            if library.image_tags and "Primary" in library.image_tags and library.image_item_id:
                api_key = settings.jellyfin_api_key
                # Use image_item_id which could be library ID or first item ID
                library.image_url = f"{jellyfin_client.base_url}Items/{library.image_item_id}/Images/Primary?api_key={api_key}"
            else:
                library.image_url = None

        return LibraryListResponse(
            libraries=libraries,
            total=len(libraries),
        )

    except JellyfinError as e:
        logger.error(f"Failed to list libraries: {e}")
        raise HTTPException(status_code=502, detail=f"Jellyfin error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing libraries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/libraries/{library_id}/items", response_model=ItemListResponse)
async def list_library_items(
    library_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    has_subtitle: bool | None = Query(default=None, description="Filter by subtitle presence"),
    db: Session = Depends(get_db),
):
    """
    List items in a Jellyfin library with pagination.
    Returns Series for tvshows libraries, Movies for movie libraries.

    Args:
        library_id: Library ID to query
        limit: Max items per page (1-500)
        offset: Pagination offset
        has_subtitle: Filter items by subtitle presence (optional)

    Returns:
        Paginated list of items (Series/Movies, not individual episodes)
    """
    try:
        jellyfin_client = get_jellyfin_client()

        # Get library info to determine collection type
        libraries = await jellyfin_client.list_libraries()
        library = next((lib for lib in libraries if lib.id == library_id), None)

        if not library:
            raise HTTPException(status_code=404, detail="Library not found")

        # Determine item types based on library collection type
        include_item_types = []
        if library.type == "tvshows":
            include_item_types = ["Series"]
        elif library.type == "movies":
            include_item_types = ["Movie"]
        else:
            # For other types (boxsets, mixed, etc), include both
            include_item_types = ["Series", "Movie"]

        # Build filters
        filters = {"IncludeItemTypes": ",".join(include_item_types)}

        if has_subtitle is not None:
            filters["HasSubtitles"] = str(has_subtitle).lower()

        # Get items with MediaStreams and additional metadata fields
        response = await jellyfin_client.get_library_items(
            library_id=library_id,
            limit=limit,
            start_index=offset,
            recursive=True,
            fields=[
                "MediaStreams",
                "Path",
                "Overview",
                "Genres",
                "ProductionYear",
                "CommunityRating",
                "OfficialRating",
                "PremiereDate",
                "ChildCount",  # Number of seasons/episodes for series
            ],
            filters=filters,
        )

        items = response.get("Items", [])
        total = response.get("TotalRecordCount", 0)

        # Use LanguageDetector to analyze media items
        detector = LanguageDetector()
        # 从自动翻译规则推断需要检测的语言
        from app.services.detector import get_required_langs_from_rules

        required_langs = get_required_langs_from_rules(db)

        # Process items with full media information
        processed_items = []
        for item_data in items:
            # Convert dict to JellyfinItem model
            try:
                item = JellyfinItem.model_validate(item_data)
            except Exception as e:
                logger.warning(f"Failed to parse item {item_data.get('Id')}: {e}")
                continue

            # Extract language information
            audio_langs = detector.extract_audio_languages(item)
            subtitle_langs = detector.extract_subtitle_languages(item)
            subtitle_streams = detector.extract_subtitle_streams(item)  # Get all subtitle streams
            missing_langs = detector.detect_missing_languages(item, required_langs, db_session=db)

            # Get duration and file size from first media source
            media_sources = item.media_sources
            duration_seconds = None
            file_size_bytes = None

            if media_sources:
                first_source = media_sources[0]
                # Duration is in ticks (1 tick = 100 nanoseconds)
                run_time_ticks = first_source.run_time_ticks
                if run_time_ticks:
                    duration_seconds = int(run_time_ticks / 10_000_000)  # Convert to seconds
                file_size_bytes = first_source.size

            # Generate image URLs with API key for authentication
            image_url = None
            backdrop_url = None
            api_key = settings.jellyfin_api_key
            if hasattr(item, "image_tags") and item.image_tags:
                # Primary image (poster)
                if "Primary" in item.image_tags:
                    image_url = f"{jellyfin_client.base_url}Items/{item.id}/Images/Primary?api_key={api_key}"
                # Backdrop image
                if "Backdrop" in item.image_tags:
                    backdrop_url = f"{jellyfin_client.base_url}Items/{item.id}/Images/Backdrop?api_key={api_key}"

            # Extract additional metadata from raw item data
            production_year = item_data.get("ProductionYear")
            community_rating = item_data.get("CommunityRating")
            official_rating = item_data.get("OfficialRating")
            overview = item_data.get("Overview")
            genres = item_data.get("Genres", [])
            child_count = item_data.get("ChildCount", 0)  # Number of episodes/seasons

            processed_items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "type": item.type,
                    "path": item.path,
                    "audio_languages": audio_langs,
                    "subtitle_languages": subtitle_langs,
                    "subtitle_streams": subtitle_streams,  # Add full subtitle stream info
                    "missing_languages": missing_langs,
                    "duration_seconds": duration_seconds,
                    "file_size_bytes": file_size_bytes,
                    # New metadata fields
                    "image_url": image_url,
                    "backdrop_url": backdrop_url,
                    "production_year": production_year,
                    "community_rating": community_rating,
                    "official_rating": official_rating,
                    "overview": overview,
                    "genres": genres,
                    "series_name": item.name if item.type == "Series" else None,
                    "child_count": child_count,
                }
            )

        return ItemListResponse(
            items=processed_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except JellyfinNotFoundError:
        raise HTTPException(status_code=404, detail="Library not found")
    except JellyfinError as e:
        logger.error(f"Failed to list library items: {e}")
        raise HTTPException(status_code=502, detail=f"Jellyfin error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(
    item_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a Jellyfin item with language analysis.

    Args:
        item_id: Jellyfin item ID

    Returns:
        Item details with existing and missing languages
    """
    try:
        jellyfin_client = get_jellyfin_client()

        # Get item with MediaStreams
        item = await jellyfin_client.get_item(
            item_id=item_id,
            fields=["MediaStreams", "Path", "MediaSources"],
        )

        # Analyze languages
        detector = LanguageDetector()
        existing_subtitles = detector.extract_subtitle_languages(item)
        existing_audio = detector.extract_audio_languages(item)

        # 从自动翻译规则推断需要检测的语言
        from app.services.detector import get_required_langs_from_rules

        required_langs = get_required_langs_from_rules(db)
        missing_subtitles = detector.detect_missing_languages(item, required_langs, db_session=db)

        return ItemDetailResponse(
            item=item,
            existing_subtitle_langs=existing_subtitles,
            existing_audio_langs=existing_audio,
            missing_subtitle_langs=missing_subtitles,
        )

    except JellyfinNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found")
    except JellyfinError as e:
        logger.error(f"Failed to get item detail: {e}")
        raise HTTPException(status_code=502, detail=f"Jellyfin error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error getting item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/series/{series_id}/episodes", response_model=ItemListResponse)
async def list_series_episodes(
    series_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all episodes for a TV series.

    Args:
        series_id: Series ID from Jellyfin
        limit: Max episodes per page (1-1000)
        offset: Pagination offset

    Returns:
        Paginated list of episodes with language information
    """
    try:
        jellyfin_client = get_jellyfin_client()

        # Get all episodes for this series
        filters = {
            "IncludeItemTypes": "Episode",
            "ParentId": series_id,
        }

        response = await jellyfin_client.get_library_items(
            library_id=None,  # Don't restrict by library, use ParentId instead
            limit=limit,
            start_index=offset,
            recursive=True,
            fields=[
                "MediaStreams",
                "Path",
                "Overview",
                "SeriesName",
                "SeasonName",
                "IndexNumber",
                "ParentIndexNumber",
                "ProductionYear",
                "PremiereDate",
            ],
            filters=filters,
        )

        items = response.get("Items", [])
        total = response.get("TotalRecordCount", 0)

        # Use LanguageDetector to analyze episodes
        detector = LanguageDetector()
        # 从自动翻译规则推断需要检测的语言
        from app.services.detector import get_required_langs_from_rules

        required_langs = get_required_langs_from_rules(db)

        # Process episodes
        processed_items = []
        for item_data in items:
            try:
                item = JellyfinItem.model_validate(item_data)
            except Exception as e:
                logger.warning(f"Failed to parse episode {item_data.get('Id')}: {e}")
                continue

            # Extract language information
            audio_langs = detector.extract_audio_languages(item)
            subtitle_langs = detector.extract_subtitle_languages(item)
            subtitle_streams = detector.extract_subtitle_streams(item)  # Get all subtitle streams
            missing_langs = detector.detect_missing_languages(item, required_langs, db_session=db)

            # Get duration and file size
            media_sources = item.media_sources
            duration_seconds = None
            file_size_bytes = None

            if media_sources:
                first_source = media_sources[0]
                run_time_ticks = first_source.run_time_ticks
                if run_time_ticks:
                    duration_seconds = int(run_time_ticks / 10_000_000)
                file_size_bytes = first_source.size

            # Generate image URLs
            image_url = None
            api_key = settings.jellyfin_api_key
            if hasattr(item, "image_tags") and item.image_tags and "Primary" in item.image_tags:
                image_url = (
                    f"{jellyfin_client.base_url}Items/{item.id}/Images/Primary?api_key={api_key}"
                )

            # Extract episode metadata
            series_name = item_data.get("SeriesName")
            season_name = item_data.get("SeasonName")
            episode_number = item_data.get("IndexNumber")
            season_number = item_data.get("ParentIndexNumber")
            production_year = item_data.get("ProductionYear")
            overview = item_data.get("Overview")

            processed_items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "type": item.type,
                    "path": item.path,
                    "audio_languages": audio_langs,
                    "subtitle_languages": subtitle_langs,
                    "subtitle_streams": subtitle_streams,  # Add full subtitle stream info
                    "missing_languages": missing_langs,
                    "duration_seconds": duration_seconds,
                    "file_size_bytes": file_size_bytes,
                    "image_url": image_url,
                    "production_year": production_year,
                    "overview": overview,
                    "series_name": series_name,
                    "season_name": season_name,
                    "episode_number": episode_number,
                    "season_number": season_number,
                }
            )

        return ItemListResponse(
            items=processed_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except JellyfinError as e:
        logger.error(f"Failed to list series episodes: {e}")
        raise HTTPException(status_code=502, detail=f"Jellyfin error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing episodes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Scan Endpoints
# =============================================================================


@router.post("/scan", response_model=ScanJobResponse)
async def trigger_scan(
    request: ScanLibraryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Trigger a library scan for missing subtitles.

    Creates a Celery task that will:
    1. Scan library for media items
    2. Detect missing subtitle languages
    3. Create translation jobs for missing languages

    Args:
        request: Scan configuration
        db: Database session

    Returns:
        Scan job information
    """
    try:
        # Get required languages (use request override or infer from rules)
        if request.required_langs:
            required_langs = request.required_langs
        else:
            from app.services.detector import get_required_langs_from_rules

            required_langs = get_required_langs_from_rules(db)

        # Submit scan task to Celery
        task = scan_library_task.apply_async(
            kwargs={
                "library_id": request.library_id,
                "required_langs": required_langs,
                "force_rescan": request.force_rescan,
            },
            queue="scan",
            priority=3,  # Medium priority
        )

        logger.info(
            f"Scan task created: {task.id} "
            f"(library={request.library_id or 'all'}, langs={required_langs})"
        )

        return ScanJobResponse(
            job_id=str(task.id),
            status="queued",
            message=f"Scan task queued for library {request.library_id or 'all'}",
        )

    except Exception as e:
        logger.error(f"Failed to create scan task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create scan task: {str(e)}")


# =============================================================================
# Writeback Endpoints
# =============================================================================


@router.post("/writeback", response_model=WritebackResponse)
async def manual_writeback(
    request: WritebackRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Manually trigger writeback for a subtitle.

    Useful for re-uploading subtitles or switching writeback mode.

    Args:
        request: Writeback configuration
        db: Database session

    Returns:
        Writeback result
    """
    try:
        # Execute writeback (async operation in threadpool for DB session)
        result = await WritebackService.writeback_subtitle(
            session=db,
            subtitle_id=str(request.subtitle_id),
            mode=None,  # Use default from settings
            force=request.force_upload,
        )

        return WritebackResponse(
            success=result["success"],
            mode=result["mode"],
            destination=result["destination"],
            message=result["message"],
        )

    except WritebackError as e:
        logger.error(f"Writeback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during writeback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Health Check
# =============================================================================


@router.get("/health")
async def jellyfin_health(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Check Jellyfin connectivity.

    Returns:
        Connection status and server info
    """
    try:
        jellyfin_client = get_jellyfin_client()
        is_connected = await jellyfin_client.check_connection()

        if is_connected:
            return {
                "status": "healthy",
                "connected": True,
                "message": "Jellyfin connection successful",
            }
        else:
            return {
                "status": "unhealthy",
                "connected": False,
                "message": "Cannot connect to Jellyfin",
            }

    except Exception as e:
        logger.error(f"Jellyfin health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "message": str(e),
        }
