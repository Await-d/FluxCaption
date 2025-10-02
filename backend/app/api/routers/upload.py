"""
File upload endpoints.

Handles subtitle file uploads for translation.
"""

import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.upload import UploadResponse, UploadError
from app.services.subtitle_service import SubtitleService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/upload", tags=["Upload"])


# Allowed subtitle file extensions
ALLOWED_EXTENSIONS = {'.srt', '.ass', '.ssa', '.vtt'}
MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024  # Convert MB to bytes


@router.post(
    "/subtitle",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload subtitle file",
    responses={
        201: {"description": "File uploaded successfully"},
        400: {"model": UploadError, "description": "Invalid file"},
        413: {"model": UploadError, "description": "File too large"},
    },
)
async def upload_subtitle(
    file: UploadFile = File(..., description="Subtitle file to upload"),
) -> UploadResponse:
    """
    Upload a subtitle file for translation.

    Accepts .srt, .ass, .ssa, and .vtt files.

    Args:
        file: Subtitle file (multipart/form-data)

    Returns:
        UploadResponse: Upload information

    Raises:
        HTTPException: If file is invalid or too large
    """
    try:
        # Validate filename exists
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )

        # Generate unique file ID and path
        file_id = str(uuid.uuid4())
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Save file with unique name
        file_path = temp_dir / f"{file_id}{file_ext}"

        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(
            f"Uploaded subtitle file: {file.filename} ({file_size} bytes) -> {file_path}"
        )

        # Validate subtitle file can be parsed
        try:
            if not SubtitleService.validate_file(str(file_path)):
                # Delete invalid file
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid subtitle file format or corrupted file",
                )
        except Exception as e:
            # Delete file on validation error
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse subtitle file: {str(e)}",
            )

        # Detect format
        detected_format = SubtitleService.detect_format(str(file_path))

        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            path=str(file_path),
            size=file_size,
            format=detected_format,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )
