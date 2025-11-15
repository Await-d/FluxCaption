"""
Runtime configuration loader.

Loads configuration from database settings, with fallback to environment variables.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.setting import Setting
from app.core.config import settings as env_settings

logger = get_logger(__name__)


class RuntimeConfig:
    """
    Runtime configuration that loads from database with environment variable fallback.
    """

    def __init__(self, db: Session = None):
        """
        Initialize runtime config.

        Args:
            db: Database session (optional, will use lazy loading if not provided)
        """
        self.db = db
        self._cache = {}

    def get_int(self, key: str, fallback: Optional[int] = None) -> int:
        """
        Get integer configuration value.

        First checks database, then environment variable, then fallback.

        Args:
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            Configuration value as integer
        """
        # Check cache first
        if key in self._cache:
            try:
                return int(self._cache[key])
            except (ValueError, TypeError):
                pass

        # Try database
        if self.db:
            try:
                stmt = select(Setting).where(Setting.key == key)
                setting = self.db.scalar(stmt)
                if setting:
                    self._cache[key] = setting.value
                    return int(setting.value)
            except Exception as e:
                logger.warning(f"Failed to load setting {key} from database: {e}")

        # Fallback to environment variable
        try:
            env_value = getattr(env_settings, key, None)
            if env_value is not None:
                return int(env_value)
        except (ValueError, TypeError, AttributeError):
            pass

        # Use fallback
        if fallback is not None:
            return fallback

        raise ValueError(f"Configuration key '{key}' not found and no fallback provided")

    def get_str(self, key: str, fallback: Optional[str] = None) -> str:
        """
        Get string configuration value.

        Args:
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            Configuration value as string
        """
        # Check cache first
        if key in self._cache:
            return str(self._cache[key])

        # Try database
        if self.db:
            try:
                stmt = select(Setting).where(Setting.key == key)
                setting = self.db.scalar(stmt)
                if setting:
                    self._cache[key] = setting.value
                    return setting.value
            except Exception as e:
                logger.warning(f"Failed to load setting {key} from database: {e}")

        # Fallback to environment variable
        try:
            env_value = getattr(env_settings, key, None)
            if env_value is not None:
                return str(env_value)
        except AttributeError:
            pass

        # Use fallback
        if fallback is not None:
            return fallback

        raise ValueError(f"Configuration key '{key}' not found and no fallback provided")

    def refresh(self):
        """Clear cache to force reload from database."""
        self._cache.clear()


# Global runtime config instance (will be initialized with database session)
_runtime_config: Optional[RuntimeConfig] = None


def get_runtime_config(db: Session = None) -> RuntimeConfig:
    """
    Get runtime configuration instance.

    Args:
        db: Database session (optional)

    Returns:
        RuntimeConfig instance
    """
    global _runtime_config

    if _runtime_config is None:
        _runtime_config = RuntimeConfig(db)
    elif db is not None and _runtime_config.db is None:
        _runtime_config.db = db

    return _runtime_config


def load_config_from_db(db: Session):
    """
    Preload configuration from database.

    This should be called during application startup to cache configuration values.

    Args:
        db: Database session
    """
    config = get_runtime_config(db)

    # Preload common configuration keys
    keys_to_preload = [
        "asr_auto_segment_threshold",
        "task_resume_paused_jobs_interval",
        "task_check_quota_limits_interval",
        "task_quota_check_cache_ttl",
        "translation_batch_size",
        "translation_max_line_length",
    ]

    for key in keys_to_preload:
        try:
            config.get_int(key, fallback=getattr(env_settings, key, 0))
        except Exception as e:
            logger.warning(f"Failed to preload config key {key}: {e}")

    logger.info(f"Preloaded {len(keys_to_preload)} configuration keys from database")
