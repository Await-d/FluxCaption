"""
Job management schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Request to create a translation job."""

    source_type: str = Field(description="Source type: subtitle | audio | media")
    source_path: str | None = Field(default=None, description="Source file path or item ID")
    item_id: str | None = Field(default=None, description="Jellyfin item ID")
    source_lang: str = Field(default="auto", description="Source language (BCP-47 or 'auto')")
    target_langs: list[str] = Field(description="Target languages (BCP-47 codes)")
    model: str | None = Field(
        default=None, description="Model to use (uses default if not specified)"
    )
    provider: str | None = Field(
        default=None, description="AI provider to use (auto-selects if not specified)"
    )
    writeback_mode: str = Field(default="upload", description="Writeback mode: upload | sidecar")
    priority: int = Field(default=5, description="Job priority (1-10, higher = more important)")


class JobStatus(BaseModel):
    """Job status information."""

    status: str = Field(description="Job status: queued | running | success | failed | canceled")
    progress: float = Field(description="Progress percentage (0-100)")
    current_phase: str | None = Field(default=None, description="Current phase")
    error: str | None = Field(default=None, description="Error message if failed")


class JobResponse(BaseModel):
    """Full job information response."""

    id: UUID = Field(description="Job ID")
    item_id: str | None = Field(default=None, description="Jellyfin item ID")
    source_type: str = Field(description="Source type")
    source_path: str | None = Field(default=None, description="Source path")
    source_lang: str = Field(description="Source language")
    target_langs: list[str] = Field(description="Target languages")
    model: str = Field(description="Model used")
    provider: str | None = Field(default=None, description="AI provider used")
    status: str = Field(description="Job status")
    progress: float = Field(description="Progress percentage")
    current_phase: str | None = Field(default=None, description="Current phase")
    error: str | None = Field(default=None, description="Error message")
    created_at: datetime = Field(description="Creation timestamp")
    started_at: datetime | None = Field(default=None, description="Start timestamp")
    finished_at: datetime | None = Field(default=None, description="Finish timestamp")
    result_paths: list[str] | None = Field(default=None, description="Result file paths")
    metrics: dict | None = Field(default=None, description="Performance metrics")

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    jobs: list[JobResponse] = Field(description="List of jobs")
    total: int = Field(description="Total number of jobs")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")


class JobEventData(BaseModel):
    """SSE event data for job progress."""

    job_id: str = Field(description="Job ID")
    phase: str = Field(description="Current phase")
    status: str = Field(description="Status message")
    progress: float = Field(description="Progress percentage")
    completed: int | None = Field(default=None, description="Completed units")
    total: int | None = Field(default=None, description="Total units")
    error: str | None = Field(default=None, description="Error message")
