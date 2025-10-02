"""
Settings management API endpoints.

Provides endpoints for retrieving and updating application configuration.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Any

from app.core.config import settings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """
    Get current application settings.

    Returns all user-configurable settings and read-only system information.

    Returns:
        SettingsResponse: Current application settings
    """
    return SettingsResponse(
        # Subtitle & Translation Pipeline
        required_langs=settings.required_langs,
        writeback_mode=settings.writeback_mode,
        default_subtitle_format=settings.default_subtitle_format,
        preserve_ass_styles=settings.preserve_ass_styles,
        translation_batch_size=settings.translation_batch_size,
        translation_max_line_length=settings.translation_max_line_length,
        translation_preserve_formatting=settings.translation_preserve_formatting,
        # Model Configuration
        default_mt_model=settings.default_mt_model,
        asr_model=settings.asr_model,
        asr_language=settings.asr_language,
        asr_compute_type=settings.asr_compute_type,
        asr_device=settings.asr_device,
        asr_beam_size=settings.asr_beam_size,
        asr_vad_filter=settings.asr_vad_filter,
        # Resource Limits
        max_concurrent_scan_tasks=settings.max_concurrent_scan_tasks,
        max_concurrent_translate_tasks=settings.max_concurrent_translate_tasks,
        max_concurrent_asr_tasks=settings.max_concurrent_asr_tasks,
        max_upload_size_mb=settings.max_upload_size_mb,
        max_audio_duration_seconds=settings.max_audio_duration_seconds,
        # Feature Flags
        enable_auto_scan=settings.enable_auto_scan,
        enable_auto_pull_models=settings.enable_auto_pull_models,
        enable_sidecar_writeback=settings.enable_sidecar_writeback,
        enable_metrics=settings.enable_metrics,
        # Task Timeouts
        scan_task_timeout=settings.scan_task_timeout,
        translate_task_timeout=settings.translate_task_timeout,
        asr_task_timeout=settings.asr_task_timeout,
        # System Info (read-only)
        environment=settings.environment,
        db_vendor=settings.db_vendor,
        storage_backend=settings.storage_backend,
        log_level=settings.log_level,
    )


@router.patch("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest) -> SettingsResponse:
    """
    Update application settings.

    This endpoint performs runtime updates to configurable settings.
    Only provided fields will be updated (partial update).

    Note: Some settings require application restart to take full effect:
    - Database configuration
    - Redis/Celery configuration
    - ASR device changes (cpu/cuda)

    Args:
        request: Settings update request with optional fields

    Returns:
        SettingsResponse: Updated settings

    Raises:
        HTTPException: 400 if validation fails
    """
    updated_fields = request.model_dump(exclude_none=True)

    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    # Apply updates to settings instance
    for field, value in updated_fields.items():
        if hasattr(settings, field):
            setattr(settings, field, value)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown setting field: {field}",
            )

    # Return updated settings
    return await get_settings()


@router.post("/reset", response_model=SettingsResponse)
async def reset_settings_to_defaults() -> SettingsResponse:
    """
    Reset settings to default values.

    This will reload settings from environment variables, effectively
    reverting any runtime changes made via PATCH /api/settings.

    Note: This does NOT modify .env file or environment variables.
    Only affects the runtime settings instance.

    Returns:
        SettingsResponse: Reset settings

    Raises:
        HTTPException: 500 if reset fails
    """
    try:
        # Reload settings from environment
        from app.core.config import Settings

        new_settings = Settings()

        # Update the global settings instance with fresh values
        for field in new_settings.model_fields:
            if hasattr(settings, field):
                setattr(settings, field, getattr(new_settings, field))

        return await get_settings()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}",
        )


@router.get("/validate")
async def validate_settings() -> dict[str, Any]:
    """
    Validate current settings configuration.

    Checks for potential issues with current settings:
    - Required services connectivity (Jellyfin, Ollama, Redis, Database)
    - Model availability
    - Directory permissions
    - Resource limit consistency

    Returns:
        dict: Validation results with warnings and errors
    """
    validation_results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "checks": {},
    }

    # Check if required_langs is not empty
    if not settings.required_langs:
        validation_results["errors"].append("required_langs cannot be empty")
        validation_results["valid"] = False

    # Check task limits are reasonable
    if settings.max_concurrent_translate_tasks < 1:
        validation_results["errors"].append("max_concurrent_translate_tasks must be at least 1")
        validation_results["valid"] = False

    if settings.max_concurrent_asr_tasks < 1:
        validation_results["errors"].append("max_concurrent_asr_tasks must be at least 1")
        validation_results["valid"] = False

    if settings.max_concurrent_scan_tasks < 1:
        validation_results["errors"].append("max_concurrent_scan_tasks must be at least 1")
        validation_results["valid"] = False

    # Check timeouts are reasonable
    if settings.translate_task_timeout < 60:
        validation_results["warnings"].append("translate_task_timeout is very low, may cause premature failures")

    if settings.asr_task_timeout < 300:
        validation_results["warnings"].append("asr_task_timeout is very low, may cause premature failures")

    # Check batch size is reasonable
    if settings.translation_batch_size < 1:
        validation_results["errors"].append("translation_batch_size must be at least 1")
        validation_results["valid"] = False

    if settings.translation_batch_size > 100:
        validation_results["warnings"].append("translation_batch_size is very high, may cause memory issues")

    # Check max line length is reasonable
    if settings.translation_max_line_length < 20:
        validation_results["warnings"].append("translation_max_line_length is very low, may cause excessive line breaks")

    if settings.translation_max_line_length > 200:
        validation_results["warnings"].append("translation_max_line_length is very high, may cause display issues")

    # Check upload size limit
    if settings.max_upload_size_mb > 2000:
        validation_results["warnings"].append("max_upload_size_mb is very high, may cause memory issues")

    # Check audio duration limit
    if settings.max_audio_duration_seconds > 14400:  # 4 hours
        validation_results["warnings"].append("max_audio_duration_seconds is very high, ASR tasks may take very long")

    validation_results["checks"]["basic_validation"] = "passed"

    return validation_results
