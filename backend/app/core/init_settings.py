"""
System settings initialization.

Initialize default system configuration values in the database.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.setting import Setting

logger = logging.getLogger(__name__)


# Configuration validation constraints
CONFIG_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "asr_auto_segment_threshold": {
        "min": 60,           # At least 1 minute
        "max": 7200,         # Max 2 hours
        "step": 60,          # 1 minute steps
        "unit": "seconds",
        "description_suffix": "Must be between 60 and 7200 seconds"
    },
    "task_resume_paused_jobs_interval": {
        "min": 300,          # At least 5 minutes
        "max": 86400,        # Max 24 hours
        "step": 300,         # 5 minute steps
        "unit": "seconds",
        "description_suffix": "Must be between 300 and 86400 seconds"
    },
    "task_check_quota_limits_interval": {
        "min": 300,          # At least 5 minutes
        "max": 86400,        # Max 24 hours
        "step": 300,         # 5 minute steps
        "unit": "seconds",
        "description_suffix": "Must be between 300 and 86400 seconds"
    },
    "task_quota_check_cache_ttl": {
        "min": 10,           # At least 10 seconds
        "max": 600,          # Max 10 minutes
        "step": 10,          # 10 second steps
        "unit": "seconds",
        "description_suffix": "Must be between 10 and 600 seconds"
    },
    "translation_batch_size": {
        "min": 1,
        "max": 100,
        "step": 1,
        "unit": "lines",
        "description_suffix": "Must be between 1 and 100 lines"
    },
    "translation_max_line_length": {
        "min": 20,
        "max": 200,
        "step": 1,
        "unit": "characters",
        "description_suffix": "Must be between 20 and 200 characters"
    },
}


def validate_setting_value(key: str, value: str) -> tuple[bool, Optional[str]]:
    """
    Validate setting value against constraints.

    Args:
        key: Setting key
        value: Value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get constraints for this key
    constraints = CONFIG_CONSTRAINTS.get(key)
    if not constraints:
        # No constraints defined, allow any value
        return True, None

    try:
        # Try to parse as int
        int_value = int(value)

        # Check min constraint
        if "min" in constraints and int_value < constraints["min"]:
            return False, (
                f"Value must be at least {constraints['min']} {constraints.get('unit', '')}. "
                f"{constraints.get('description_suffix', '')}"
            )

        # Check max constraint
        if "max" in constraints and int_value > constraints["max"]:
            return False, (
                f"Value must not exceed {constraints['max']} {constraints.get('unit', '')}. "
                f"{constraints.get('description_suffix', '')}"
            )

        # All checks passed
        return True, None

    except (ValueError, TypeError):
        return False, f"Value must be a valid integer"


def init_system_settings(db: Session) -> None:
    """
    Initialize system settings with default values.

    These settings can be managed through the admin UI and override
    environment variable defaults.

    Args:
        db: Database session
    """
    # Import settings to get default values (single source of truth)
    from app.core.config import settings as config

    # Define default system settings
    # NOTE: Default values are pulled from Settings class to avoid duplication
    default_settings = [
        # ASR Configuration
        {
            "key": "asr_auto_segment_threshold",
            "value": str(config.asr_auto_segment_threshold),
            "description": "Audio duration threshold (seconds) for automatic segmentation. Videos longer than this will be split into segments for ASR processing.",
            "category": "asr",
            "is_editable": True,
            "value_type": "int"
        },

        # Task Scheduling Configuration
        {
            "key": "task_resume_paused_jobs_interval",
            "value": str(config.task_resume_paused_jobs_interval),
            "description": "Interval in seconds to check and resume paused jobs (default: 1 hour). Paused jobs will be automatically resumed when their quota resets.",
            "category": "tasks",
            "is_editable": True,
            "value_type": "int"
        },
        {
            "key": "task_check_quota_limits_interval",
            "value": str(config.task_check_quota_limits_interval),
            "description": "Interval in seconds to check quota limits (default: 2 hours). System will periodically verify quota status and pause jobs if needed.",
            "category": "tasks",
            "is_editable": True,
            "value_type": "int"
        },
        {
            "key": "task_quota_check_cache_ttl",
            "value": str(config.task_quota_check_cache_ttl),
            "description": "Time-to-live for quota check cache in seconds (default: 1 minute). Caching reduces database queries during translation loops.",
            "category": "tasks",
            "is_editable": True,
            "value_type": "int"
        },

        # Translation Configuration
        {
            "key": "translation_batch_size",
            "value": str(config.translation_batch_size),
            "description": "Number of subtitle lines to translate in a single batch. Larger batches improve efficiency but use more memory.",
            "category": "translation",
            "is_editable": True,
            "value_type": "int"
        },
        {
            "key": "translation_max_line_length",
            "value": str(config.translation_max_line_length),
            "description": "Maximum character length per subtitle line. Lines exceeding this will be split.",
            "category": "translation",
            "is_editable": True,
            "value_type": "int"
        },
    ]

    # Insert or update settings
    updated_count = 0
    created_count = 0

    for setting_data in default_settings:
        # Check if setting already exists
        stmt = select(Setting).where(Setting.key == setting_data["key"])
        existing = db.scalar(stmt)

        if existing:
            # Update description and metadata, but keep existing value
            existing.description = setting_data["description"]
            existing.category = setting_data["category"]
            existing.is_editable = setting_data["is_editable"]
            existing.value_type = setting_data["value_type"]
            updated_count += 1
        else:
            # Create new setting with default value
            new_setting = Setting(**setting_data)
            db.add(new_setting)
            created_count += 1

    db.commit()

    logger.info(
        f"System settings initialized: {created_count} created, {updated_count} updated"
    )


def get_setting_value(db: Session, key: str, default: str = None) -> str:
    """
    Get setting value from database.

    Args:
        db: Database session
        key: Setting key
        default: Default value if setting not found

    Returns:
        Setting value or default
    """
    stmt = select(Setting).where(Setting.key == key)
    setting = db.scalar(stmt)

    if setting:
        return setting.value
    return default


def get_setting_int(db: Session, key: str, default: int = None) -> int:
    """
    Get integer setting value from database.

    Args:
        db: Database session
        key: Setting key
        default: Default value if setting not found

    Returns:
        Integer setting value or default
    """
    value = get_setting_value(db, key)
    if value is not None:
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for setting {key}: {value}")
    return default


def update_setting(db: Session, key: str, value: str, updated_by: str = "system") -> None:
    """
    Update setting value in database.

    Args:
        db: Database session
        key: Setting key
        value: New value
        updated_by: User who updated the setting
    """
    stmt = select(Setting).where(Setting.key == key)
    setting = db.scalar(stmt)

    if setting:
        setting.value = str(value)
        setting.updated_by = updated_by
        db.commit()
        logger.info(f"Setting {key} updated to {value} by {updated_by}")
    else:
        logger.warning(f"Attempted to update non-existent setting: {key}")
