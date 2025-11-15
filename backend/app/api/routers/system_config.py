"""
System Configuration API Router.

Provides endpoints for managing system-wide configuration settings.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.setting import Setting
from app.models.setting_change_history import SettingChangeHistory
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class SettingConstraints(BaseModel):
    """Setting validation constraints."""

    min: int | None = None
    max: int | None = None
    step: int | None = None
    unit: str | None = None
    description_suffix: str | None = None


class SettingResponse(BaseModel):
    """Setting response model."""

    key: str
    value: str
    description: str | None = None
    category: str | None = None
    is_editable: bool = True
    value_type: str = "string"
    updated_at: str
    updated_by: str | None = None
    constraints: SettingConstraints | None = None

    class Config:
        from_attributes = True


class SettingUpdateRequest(BaseModel):
    """Setting update request model."""

    value: str = Field(..., description="New value for the setting")
    change_reason: str | None = Field(None, description="Reason for the change")


class SettingChangeHistoryResponse(BaseModel):
    """Setting change history response model."""

    id: str
    setting_key: str
    old_value: str | None
    new_value: str
    changed_by: str
    change_reason: str | None
    created_at: str

    class Config:
        from_attributes = True


class SystemConfigCategory(BaseModel):
    """System configuration category."""

    category: str
    label: str
    description: str
    settings: list[SettingResponse]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/system/config",
    response_model=list[SystemConfigCategory],
    tags=["system"],
    summary="Get all system configuration settings",
    description="Returns all system configuration settings grouped by category. "
    "Only returns editable settings that can be modified by administrators.",
    responses={
        200: {
            "description": "List of configuration categories with their settings",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "category": "asr",
                            "label": "ASR / 语音识别",
                            "description": "Automatic Speech Recognition configuration",
                            "settings": [
                                {
                                    "key": "asr_auto_segment_threshold",
                                    "value": "1800",
                                    "description": "Threshold for automatic audio segmentation",
                                    "category": "asr",
                                    "is_editable": True,
                                    "value_type": "int",
                                    "updated_at": "2025-11-15T10:00:00Z",
                                    "updated_by": "admin",
                                    "constraints": {
                                        "min": 60,
                                        "max": 7200,
                                        "step": 60,
                                        "unit": "seconds",
                                    },
                                }
                            ],
                        }
                    ]
                }
            },
        }
    },
)
async def get_system_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[SystemConfigCategory]:
    """
    Get all system configuration settings grouped by category.

    Returns:
        List of configuration categories with their settings
    """
    # Import constraints
    from app.core.init_settings import CONFIG_CONSTRAINTS

    # Get all editable settings ordered by category
    stmt = select(Setting).where(Setting.is_editable).order_by(Setting.category, Setting.key)
    settings = db.scalars(stmt).all()

    # Group by category
    categories_dict = {}
    for setting in settings:
        cat = setting.category or "general"
        if cat not in categories_dict:
            categories_dict[cat] = []

        # Build response with constraints
        setting_response = SettingResponse.model_validate(setting)

        # Add constraints if available
        if setting.key in CONFIG_CONSTRAINTS:
            setting_response.constraints = SettingConstraints(**CONFIG_CONSTRAINTS[setting.key])

        categories_dict[cat].append(setting_response)

    # Define category labels and descriptions
    category_info = {
        "asr": {
            "label": "ASR / 语音识别",
            "description": "Automatic Speech Recognition configuration",
        },
        "tasks": {
            "label": "Tasks / 定时任务",
            "description": "Scheduled task intervals and caching",
        },
        "translation": {
            "label": "Translation / 翻译",
            "description": "Translation pipeline configuration",
        },
        "general": {"label": "General / 通用", "description": "General system configuration"},
    }

    # Build response
    result = []
    for category, settings_list in categories_dict.items():
        info = category_info.get(category, {"label": category.title(), "description": ""})
        result.append(
            SystemConfigCategory(
                category=category,
                label=info["label"],
                description=info["description"],
                settings=settings_list,
            )
        )

    return result


@router.get(
    "/system/config/{key}",
    response_model=SettingResponse,
    tags=["system"],
    summary="Get a specific configuration setting",
    description="Returns detailed information about a single configuration setting including "
    "its current value, constraints, and update history metadata.",
)
async def get_system_config_by_key(
    key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SettingResponse:
    """
    Get a specific system configuration setting by key.

    Args:
        key: Setting key

    Returns:
        Setting information
    """
    # Import constraints
    from app.core.init_settings import CONFIG_CONSTRAINTS

    stmt = select(Setting).where(Setting.key == key)
    setting = db.scalar(stmt)

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    # Build response with constraints
    setting_response = SettingResponse.model_validate(setting)

    # Add constraints if available
    if key in CONFIG_CONSTRAINTS:
        setting_response.constraints = SettingConstraints(**CONFIG_CONSTRAINTS[key])

    return setting_response


@router.put(
    "/system/config/{key}",
    response_model=SettingResponse,
    tags=["system"],
    summary="Update a system configuration setting",
    description="Updates a system configuration setting with a new value. "
    "Requires administrator privileges. The update is validated against "
    "defined constraints and recorded in the change history audit trail. "
    "A configuration change event is published for worker notification.",
    responses={
        200: {"description": "Setting successfully updated"},
        400: {"description": "Invalid value or setting not editable"},
        403: {"description": "Not authorized - admin privileges required"},
        404: {"description": "Setting not found"},
    },
)
async def update_system_config(
    key: str,
    request: SettingUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SettingResponse:
    """
    Update a system configuration setting.

    Requires admin privileges.

    Args:
        key: Setting key
        request: Update request with new value
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated setting information
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update system configuration",
        )

    # Get setting
    stmt = select(Setting).where(Setting.key == key)
    setting = db.scalar(stmt)

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    # Check if setting is editable
    if not setting.is_editable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setting '{key}' is not editable",
        )

    # Validate value based on type
    new_value = request.value
    try:
        if setting.value_type == "int":
            int(new_value)  # Validate can be converted to int
        elif setting.value_type == "float":
            float(new_value)  # Validate can be converted to float
        elif setting.value_type == "bool":
            if new_value.lower() not in ("true", "false", "0", "1"):
                raise ValueError("Boolean must be 'true', 'false', '0', or '1'")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value for type '{setting.value_type}': {str(e)}",
        )

    # Validate value against constraints
    from app.core.init_settings import validate_setting_value

    is_valid, error_message = validate_setting_value(key, new_value)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Record change history
    old_value = setting.value
    change_history = SettingChangeHistory(
        id=str(uuid.uuid4()),
        setting_key=key,
        old_value=old_value,
        new_value=new_value,
        changed_by=current_user.username,
        change_reason=request.change_reason,
        created_at=datetime.now(UTC),
    )
    db.add(change_history)

    # Update setting
    setting.value = new_value
    setting.updated_by = current_user.username
    db.commit()
    db.refresh(setting)

    logger.info(
        f"System setting '{key}' updated from '{old_value}' to '{new_value}' "
        f"by user '{current_user.username}'"
        + (f" - Reason: {request.change_reason}" if request.change_reason else "")
    )

    # Broadcast configuration change notification (for future worker reload)
    try:
        from app.core.events import event_publisher

        await event_publisher.publish_config_change(
            setting_key=key,
            old_value=old_value,
            new_value=new_value,
            changed_by=current_user.username,
        )
        logger.debug(f"Successfully published config change event for '{key}'")
    except Exception as e:
        # Log error but don't fail the request - setting was already updated
        logger.error(f"Failed to publish config change event for '{key}': {e}", exc_info=True)

    return SettingResponse.model_validate(setting)


@router.post(
    "/system/config/{key}/reset",
    response_model=SettingResponse,
    tags=["system"],
    summary="Reset a configuration setting to default value",
    description="Resets a system configuration setting to its default value as defined "
    "in the Settings class. Requires administrator privileges.",
    responses={
        200: {"description": "Setting successfully reset"},
        400: {"description": "No default value defined for this setting"},
        403: {"description": "Not authorized - admin privileges required"},
        404: {"description": "Setting not found"},
    },
)
async def reset_system_config(
    key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SettingResponse:
    """
    Reset a system configuration setting to its default value.

    Requires admin privileges.

    Args:
        key: Setting key
        current_user: Current authenticated user
        db: Database session

    Returns:
        Reset setting information
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reset system configuration",
        )

    # Get setting
    stmt = select(Setting).where(Setting.key == key)
    setting = db.scalar(stmt)

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    # Get default value from Settings class (single source of truth)
    from app.core.config import settings as config_settings

    # Map setting keys to their Settings class attributes
    config_key_mapping = {
        "asr_auto_segment_threshold": "asr_auto_segment_threshold",
        "task_resume_paused_jobs_interval": "task_resume_paused_jobs_interval",
        "task_check_quota_limits_interval": "task_check_quota_limits_interval",
        "task_quota_check_cache_ttl": "task_quota_check_cache_ttl",
        "translation_batch_size": "translation_batch_size",
        "translation_max_line_length": "translation_max_line_length",
    }

    config_attr = config_key_mapping.get(key)
    if not config_attr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No default value defined for setting '{key}'",
        )

    # Get default value from Settings instance
    default_value = str(getattr(config_settings, config_attr))

    # Reset to default
    old_value = setting.value
    setting.value = default_value
    setting.updated_by = current_user.username
    db.commit()
    db.refresh(setting)

    logger.info(
        f"System setting '{key}' reset from '{old_value}' to default '{default_value}' "
        f"by user '{current_user.username}'"
    )

    # Build response with constraints
    from app.core.init_settings import CONFIG_CONSTRAINTS

    setting_response = SettingResponse.model_validate(setting)

    # Add constraints if available
    if key in CONFIG_CONSTRAINTS:
        setting_response.constraints = SettingConstraints(**CONFIG_CONSTRAINTS[key])

    return setting_response


@router.get(
    "/system/config/{key}/history",
    response_model=list[SettingChangeHistoryResponse],
    tags=["system"],
    summary="Get change history for a specific setting",
    description="Returns an audit trail of all changes made to a specific configuration setting, "
    "including who made the change, when, what changed, and optionally why. "
    "Requires administrator privileges.",
    responses={
        200: {"description": "List of change history records"},
        403: {"description": "Not authorized - admin privileges required"},
    },
)
async def get_setting_change_history(
    key: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 50,
) -> list[SettingChangeHistoryResponse]:
    """
    Get change history for a specific setting.

    Args:
        key: Setting key
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of history records to return

    Returns:
        List of change history records
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view configuration history",
        )

    # Query change history, ordered by most recent first
    stmt = (
        select(SettingChangeHistory)
        .where(SettingChangeHistory.setting_key == key)
        .order_by(desc(SettingChangeHistory.created_at))
        .limit(limit)
    )
    history_records = db.scalars(stmt).all()

    return [SettingChangeHistoryResponse.model_validate(record) for record in history_records]


@router.get(
    "/system/config-history",
    response_model=list[SettingChangeHistoryResponse],
    tags=["system"],
    summary="Get recent configuration changes across all settings",
    description="Returns a global audit trail of recent configuration changes across all settings, "
    "ordered by most recent first. Useful for monitoring and auditing purposes. "
    "Requires administrator privileges.",
    responses={
        200: {"description": "List of recent configuration changes"},
        403: {"description": "Not authorized - admin privileges required"},
    },
)
async def get_all_config_changes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 100,
) -> list[SettingChangeHistoryResponse]:
    """
    Get recent configuration changes across all settings.

    Requires admin privileges.

    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Maximum number of history records to return

    Returns:
        List of change history records
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view configuration history",
        )

    # Query recent changes, ordered by most recent first
    stmt = select(SettingChangeHistory).order_by(desc(SettingChangeHistory.created_at)).limit(limit)
    history_records = db.scalars(stmt).all()

    return [SettingChangeHistoryResponse.model_validate(record) for record in history_records]
