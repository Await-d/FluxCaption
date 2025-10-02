"""
Pydantic schemas for Jellyfin API integration.

Handles request/response validation for Jellyfin endpoints with proper aliasing
for Jellyfin's PascalCase API format.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Jellyfin API Response Models
# =============================================================================

class MediaStream(BaseModel):
    """
    Represents a media stream from Jellyfin (audio, subtitle, or video).
    """
    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., alias="Type", description="Stream type: Audio, Subtitle, Video")
    index: int = Field(..., alias="Index", description="Stream index in container")
    codec: Optional[str] = Field(None, alias="Codec", description="Codec name")
    language: Optional[str] = Field(None, alias="Language", description="ISO 639-2 3-letter code")
    language_tag: Optional[str] = Field(None, alias="LanguageTag", description="BCP-47 language tag")
    display_title: Optional[str] = Field(None, alias="DisplayTitle", description="Human-readable title")
    is_default: bool = Field(False, alias="IsDefault", description="Whether this is the default stream")
    is_forced: bool = Field(False, alias="IsForced", description="Whether this is forced subtitle")
    is_external: bool = Field(False, alias="IsExternal", description="Whether this is external/sidecar")
    is_text_subtitle_stream: bool = Field(False, alias="IsTextSubtitleStream", description="Whether this is text subtitle")
    supports_external_stream: bool = Field(False, alias="SupportsExternalStream", description="Whether external streaming is supported")


class MediaSource(BaseModel):
    """
    Represents a media source from Jellyfin item.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="Id", description="Media source ID")
    path: Optional[str] = Field(None, alias="Path", description="File path to media")
    container: Optional[str] = Field(None, alias="Container", description="Container format")
    size: Optional[int] = Field(None, alias="Size", description="File size in bytes")
    media_streams: list[MediaStream] = Field(default_factory=list, alias="MediaStreams", description="Available streams")


class JellyfinLibrary(BaseModel):
    """
    Represents a Jellyfin library/collection.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="ItemId", description="Library ID")
    name: str = Field(..., alias="Name", description="Library name")
    type: Optional[str] = Field(None, alias="CollectionType", description="Type: movies, tvshows, music, etc.")
    item_count: Optional[int] = Field(None, alias="ChildCount", description="Number of items in library")
    image_url: Optional[str] = Field(None, description="Library primary image URL")


class JellyfinItem(BaseModel):
    """
    Represents a Jellyfin media item (movie, episode, etc.).
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="Id", description="Item ID")
    name: str = Field(..., alias="Name", description="Item name")
    type: str = Field(..., alias="Type", description="Item type: Movie, Episode, etc.")
    path: Optional[str] = Field(None, alias="Path", description="File system path")
    parent_id: Optional[str] = Field(None, alias="ParentId", description="Parent library/series ID")
    run_time_ticks: Optional[int] = Field(None, alias="RunTimeTicks", description="Duration in 100ns ticks")
    media_sources: list[MediaSource] = Field(default_factory=list, alias="MediaSources", description="Available media sources")
    container: Optional[str] = Field(None, alias="Container", description="Container format")
    image_tags: Optional[dict[str, str]] = Field(None, alias="ImageTags", description="Image tags for different image types")
    production_year: Optional[int] = Field(None, alias="ProductionYear", description="Year of production")
    community_rating: Optional[float] = Field(None, alias="CommunityRating", description="Community rating")
    official_rating: Optional[str] = Field(None, alias="OfficialRating", description="Official content rating")
    overview: Optional[str] = Field(None, alias="Overview", description="Plot summary/description")
    genres: list[str] = Field(default_factory=list, alias="Genres", description="Genres")
    series_name: Optional[str] = Field(None, alias="SeriesName", description="Series name (for episodes)")
    season_name: Optional[str] = Field(None, alias="SeasonName", description="Season name (for episodes)")
    index_number: Optional[int] = Field(None, alias="IndexNumber", description="Episode number")
    parent_index_number: Optional[int] = Field(None, alias="ParentIndexNumber", description="Season number")


# =============================================================================
# API Request Models
# =============================================================================

class ScanLibraryRequest(BaseModel):
    """
    Request to scan a Jellyfin library for missing subtitles.
    """
    library_id: Optional[str] = Field(None, description="Specific library ID to scan (if None, scan all)")
    required_langs: Optional[list[str]] = Field(None, description="Required languages (overrides global config)")
    force_rescan: bool = Field(False, description="Force re-scan even if recently scanned")


class WritebackRequest(BaseModel):
    """
    Request to manually writeback a subtitle to Jellyfin.
    """
    subtitle_id: UUID = Field(..., description="Subtitle record ID to writeback")
    force_upload: bool = Field(False, description="Force upload even if already uploaded")


# =============================================================================
# API Response Models
# =============================================================================

class LibraryListResponse(BaseModel):
    """
    Response for listing Jellyfin libraries.
    """
    libraries: list[JellyfinLibrary] = Field(..., description="List of available libraries")
    total: int = Field(..., description="Total count")


class ItemListResponse(BaseModel):
    """
    Response for listing items in a library.
    """
    items: list[dict] = Field(..., description="List of items (simplified)")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Offset")


class ItemDetailResponse(BaseModel):
    """
    Response for item details with language analysis.
    """
    item: JellyfinItem = Field(..., description="Full item details")
    existing_subtitle_langs: list[str] = Field(..., description="Languages with existing subtitles")
    existing_audio_langs: list[str] = Field(..., description="Languages with existing audio")
    missing_subtitle_langs: list[str] = Field(..., description="Required subtitle languages that are missing")


class ScanJobResponse(BaseModel):
    """
    Response for scan job creation.
    """
    job_id: str = Field(..., description="Celery task ID for the scan job")
    status: str = Field(..., description="Initial status (usually 'queued')")
    message: str = Field(..., description="Human-readable message")


class WritebackResponse(BaseModel):
    """
    Response for writeback operation.
    """
    success: bool = Field(..., description="Whether writeback succeeded")
    mode: str = Field(..., description="Writeback mode used: upload or sidecar")
    destination: str = Field(..., description="URL (for upload) or path (for sidecar)")
    message: str = Field(..., description="Human-readable result message")
