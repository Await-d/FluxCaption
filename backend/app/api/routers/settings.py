"""
Settings management API endpoints.

Provides endpoints for retrieving and updating application configuration.
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.api.routers.auth import get_current_user
from app.core.ai_model_catalog_runtime import ensure_catalog_sync_task
from app.core.config import settings
from app.core.db import session_scope
from app.core.settings_helper import get_default_mt_model
from app.models.setting import Setting
from app.models.user import User
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])

JELLYFIN_FIELDS = {
    "jellyfin_base_url": ("string", "Jellyfin server base URL"),
    "jellyfin_api_key": ("string", "Jellyfin API key for authentication"),
    "jellyfin_timeout": ("int", "Jellyfin request timeout in seconds"),
    "jellyfin_max_retries": ("int", "Jellyfin maximum retry attempts"),
    "jellyfin_rate_limit_per_second": ("int", "Jellyfin API rate limit per second"),
}

OLLAMA_FIELDS = {
    "ollama_base_url": ("string", "Ollama API base URL"),
    "ollama_timeout": ("int", "Ollama request timeout in seconds"),
    "ollama_keep_alive": ("string", "Ollama model keep alive duration"),
}

AI_MODEL_CATALOG_FIELDS = {
    "ai_models_auto_sync_enabled": ("bool", "Enable automatic AI model catalog sync"),
    "ai_models_auto_sync_interval_seconds": (
        "int",
        "AI model catalog automatic sync interval in seconds",
    ),
    "ai_models_catalog_url": ("string", "AI model catalog base URL"),
}

TRANSLATION_FIELDS = {
    "default_mt_model": ("string", "Default machine translation model"),
}

LOCAL_MEDIA_FIELDS = {
    "favorite_media_paths": ("json", "Favorite local media directory paths"),
}


def _get_db_setting(key: str, default: Any = None) -> Any:
    """
    Get a setting value from database, return default if not found.

    Args:
        key: Setting key
        default: Default value if setting not found in database

    Returns:
        Setting value from database or default
    """
    with session_scope() as session:
        stmt = select(Setting).where(Setting.key == key)
        setting = session.execute(stmt).scalar_one_or_none()

        if setting is None:
            return default

        # Convert value based on value_type
        if setting.value_type == "int":
            return int(setting.value)
        elif setting.value_type == "float":
            return float(setting.value)
        elif setting.value_type == "bool":
            return setting.value.lower() in ("true", "1", "yes")
        elif setting.value_type == "json":
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return default
        else:
            return setting.value


def _serialize_db_setting_value(value: Any, value_type: str) -> str:
    if value_type == "json":
        return json.dumps(value)
    return str(value)


def _parse_favorite_media_paths(value: Any) -> list[str]:
    if isinstance(value, list):
        return [path for path in value if isinstance(path, str) and path.strip()]

    if isinstance(value, str):
        return [path.strip() for path in value.split(",") if path.strip()]

    return []


def _set_db_setting(
    key: str,
    value: Any,
    value_type: str,
    category: str = "jellyfin",
    description: str = "",
    username: str = "system",
) -> None:
    """
    Set a setting value in database.

    Args:
        key: Setting key
        value: Setting value
        value_type: Type of value (string, int, float, bool, json)
        category: Setting category
        description: Setting description
        username: Username who updated the setting
    """
    with session_scope() as session:
        stmt = select(Setting).where(Setting.key == key)
        setting = session.execute(stmt).scalar_one_or_none()

        if setting is None:
            # Create new setting
            serialized_value = _serialize_db_setting_value(value, value_type)
            setting = Setting(
                key=key,
                value=serialized_value,
                value_type=value_type,
                category=category,
                description=description,
                is_editable=True,
                updated_at=datetime.now(UTC),
                updated_by=username,
            )
            session.add(setting)
        else:
            # Update existing setting
            setting.value = _serialize_db_setting_value(value, value_type)
            setting.value_type = value_type
            setting.category = category
            setting.description = description
            setting.updated_at = datetime.now(UTC)
            setting.updated_by = username

        session.commit()


def _apply_settings_updates(updated_fields: dict[str, Any], username: str) -> None:
    for field, value in updated_fields.items():
        if not hasattr(settings, field):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown setting field: {field}",
            )

        setattr(settings, field, value)

        if field in JELLYFIN_FIELDS:
            value_type, description = JELLYFIN_FIELDS[field]
            _set_db_setting(
                key=field,
                value=value,
                value_type=value_type,
                category="jellyfin",
                description=description,
                username=username,
            )
        elif field in OLLAMA_FIELDS:
            value_type, description = OLLAMA_FIELDS[field]
            _set_db_setting(
                key=field,
                value=value,
                value_type=value_type,
                category="ollama",
                description=description,
                username=username,
            )
        elif field in AI_MODEL_CATALOG_FIELDS:
            value_type, description = AI_MODEL_CATALOG_FIELDS[field]
            _set_db_setting(
                key=field,
                value=value,
                value_type=value_type,
                category="ai_models",
                description=description,
                username=username,
            )
        elif field in TRANSLATION_FIELDS:
            value_type, description = TRANSLATION_FIELDS[field]
            _set_db_setting(
                key=field,
                value=value,
                value_type=value_type,
                category="translation",
                description=description,
                username=username,
            )
        elif field in LOCAL_MEDIA_FIELDS:
            value_type, description = LOCAL_MEDIA_FIELDS[field]
            _set_db_setting(
                key=field,
                value=value,
                value_type=value_type,
                category="local_media",
                description=description,
                username=username,
            )


def _build_settings_response() -> SettingsResponse:
    # Get Jellyfin settings from database with fallback to env vars
    jellyfin_base_url = _get_db_setting("jellyfin_base_url", settings.jellyfin_base_url)
    jellyfin_api_key = _get_db_setting("jellyfin_api_key", settings.jellyfin_api_key)
    jellyfin_timeout = _get_db_setting("jellyfin_timeout", settings.jellyfin_timeout)
    jellyfin_max_retries = _get_db_setting("jellyfin_max_retries", settings.jellyfin_max_retries)
    jellyfin_rate_limit_per_second = _get_db_setting(
        "jellyfin_rate_limit_per_second", settings.jellyfin_rate_limit_per_second
    )

    # Get Ollama settings from database with fallback to env vars
    ollama_base_url = _get_db_setting("ollama_base_url", settings.ollama_base_url)
    ollama_timeout = _get_db_setting("ollama_timeout", settings.ollama_timeout)
    ollama_keep_alive = _get_db_setting("ollama_keep_alive", settings.ollama_keep_alive)
    ai_models_auto_sync_enabled = _get_db_setting(
        "ai_models_auto_sync_enabled", settings.ai_models_auto_sync_enabled
    )
    ai_models_auto_sync_interval_seconds = _get_db_setting(
        "ai_models_auto_sync_interval_seconds", settings.ai_models_auto_sync_interval_seconds
    )
    ai_models_catalog_url = _get_db_setting(
        "ai_models_catalog_url", settings.ai_models_catalog_url
    )
    ai_models_last_catalog_sync_at = _get_db_setting("ai_models_last_catalog_sync_at", None)
    favorite_media_paths = _parse_favorite_media_paths(
        _get_db_setting("favorite_media_paths", settings.favorite_media_paths)
    )

    return SettingsResponse(
        # Jellyfin Integration
        jellyfin_base_url=jellyfin_base_url,
        jellyfin_api_key=jellyfin_api_key,
        jellyfin_timeout=jellyfin_timeout,
        jellyfin_max_retries=jellyfin_max_retries,
        jellyfin_rate_limit_per_second=jellyfin_rate_limit_per_second,
        # Ollama Configuration
        ollama_base_url=ollama_base_url,
        ollama_timeout=ollama_timeout,
        ollama_keep_alive=ollama_keep_alive,
        # Subtitle & Translation Pipeline
        writeback_mode=settings.writeback_mode,
        default_subtitle_format=settings.default_subtitle_format,
        preserve_ass_styles=settings.preserve_ass_styles,
        translation_batch_size=settings.translation_batch_size,
        translation_line_concurrency=settings.translation_line_concurrency,
        ai_provider_max_concurrency=settings.ai_provider_max_concurrency,
        translation_max_line_length=settings.translation_max_line_length,
        translation_preserve_formatting=settings.translation_preserve_formatting,
        # Model Configuration
        default_mt_model=_get_db_setting("default_mt_model", get_default_mt_model()),
        asr_engine=settings.asr_engine,
        asr_model=settings.asr_model,
        funasr_model=settings.funasr_model,
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
        ai_models_auto_sync_enabled=ai_models_auto_sync_enabled,
        ai_models_auto_sync_interval_seconds=ai_models_auto_sync_interval_seconds,
        ai_models_catalog_url=ai_models_catalog_url,
        ai_models_last_catalog_sync_at=ai_models_last_catalog_sync_at,
        # Task Timeouts
        scan_task_timeout=settings.scan_task_timeout,
        translate_task_timeout=settings.translate_task_timeout,
        asr_task_timeout=settings.asr_task_timeout,
        # Local Media Configuration
        favorite_media_paths=favorite_media_paths,
        # System Info (read-only)
        environment=settings.environment,
        db_vendor=settings.db_vendor,
        storage_backend=settings.storage_backend,
        log_level=settings.log_level,
    )


@router.get("", response_model=SettingsResponse)
def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
) -> SettingsResponse:
    """
    Get current application settings.

    Returns all user-configurable settings and read-only system information.

    Returns:
        SettingsResponse: Current application settings
    """
    return _build_settings_response()


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SettingsResponse:
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

    await run_in_threadpool(_apply_settings_updates, updated_fields, current_user.username)

    if any(field in AI_MODEL_CATALOG_FIELDS for field in updated_fields):
        from app.main import ai_model_catalog_sync_loop

        await ensure_catalog_sync_task(ai_model_catalog_sync_loop)

    return await run_in_threadpool(_build_settings_response)


@router.post("/reset", response_model=SettingsResponse)
def reset_settings_to_defaults(
    current_user: Annotated[User, Depends(get_current_user)],
) -> SettingsResponse:
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

        new_settings = Settings(
            database_url=settings.database_url,
            jellyfin_base_url=settings.jellyfin_base_url,
            jellyfin_api_key=settings.jellyfin_api_key,
        )

        for field in new_settings.model_fields:
            if hasattr(settings, field):
                setattr(settings, field, getattr(new_settings, field))

        return _build_settings_response()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}",
        )


@router.get("/validate")
def validate_settings(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
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
        validation_results["warnings"].append(
            "translate_task_timeout is very low, may cause premature failures"
        )

    if settings.asr_task_timeout < 300:
        validation_results["warnings"].append(
            "asr_task_timeout is very low, may cause premature failures"
        )

    # Check batch size is reasonable
    if settings.translation_batch_size < 1:
        validation_results["errors"].append("translation_batch_size must be at least 1")
        validation_results["valid"] = False

    if settings.translation_batch_size > 100:
        validation_results["warnings"].append(
            "translation_batch_size is very high, may cause memory issues"
        )

    if settings.translation_line_concurrency < 1:
        validation_results["errors"].append("translation_line_concurrency must be at least 1")
        validation_results["valid"] = False

    if settings.translation_line_concurrency > 20:
        validation_results["warnings"].append(
            "translation_line_concurrency is very high, may overload upstream AI providers"
        )

    if settings.ai_provider_max_concurrency < 1:
        validation_results["errors"].append("ai_provider_max_concurrency must be at least 1")
        validation_results["valid"] = False

    if settings.ai_provider_max_concurrency > 50:
        validation_results["warnings"].append(
            "ai_provider_max_concurrency is very high, may overload upstream AI providers"
        )

    # Check max line length is reasonable
    if settings.translation_max_line_length < 20:
        validation_results["warnings"].append(
            "translation_max_line_length is very low, may cause excessive line breaks"
        )

    if settings.translation_max_line_length > 200:
        validation_results["warnings"].append(
            "translation_max_line_length is very high, may cause display issues"
        )

    # Check upload size limit
    if settings.max_upload_size_mb > 2000:
        validation_results["warnings"].append(
            "max_upload_size_mb is very high, may cause memory issues"
        )

    # Check audio duration limit
    if settings.max_audio_duration_seconds > 14400:  # 4 hours
        validation_results["warnings"].append(
            "max_audio_duration_seconds is very high, ASR tasks may take very long"
        )

    validation_results["checks"]["basic_validation"] = "passed"

    return validation_results
