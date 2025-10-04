"""
Helper functions for runtime settings management.

Provides dynamic settings retrieval that respects database overrides.
"""

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_default_mt_model() -> str:
    """
    Get the default MT model.

    Checks database Setting table first, falls back to config.

    Returns:
        str: Default MT model name
    """
    try:
        from app.core.db import SessionLocal
        from app.models.setting import Setting

        with SessionLocal() as db:
            default_model_setting = db.query(Setting).filter(
                Setting.key == "default_mt_model"
            ).first()

            if default_model_setting and default_model_setting.value:
                logger.debug(f"Using default model from database: {default_model_setting.value}")
                return default_model_setting.value
    except Exception as e:
        logger.warning(f"Failed to get default model from database: {e}, using config default")

    # Fallback to config
    logger.debug(f"Using default model from config: {settings.default_mt_model}")
    return settings.default_mt_model
