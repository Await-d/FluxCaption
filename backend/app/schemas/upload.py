"""
File upload schemas.
"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response after successful file upload."""

    file_id: str = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    path: str = Field(description="Server file path")
    size: int = Field(description="File size in bytes")
    format: str = Field(description="Detected subtitle format (srt/ass/vtt)")


class UploadError(BaseModel):
    """Error response for failed upload."""

    error: str = Field(description="Error message")
    detail: str | None = Field(default=None, description="Detailed error information")
