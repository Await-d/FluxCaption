"""
Database models package.

Imports all models to ensure they're registered with SQLAlchemy.
"""

from app.models.base import Base, BaseModel, BaseModelWithoutTimestamp
from app.models.types import GUID, generate_uuid
from app.models.model_registry import ModelRegistry
from app.models.translation_job import TranslationJob
from app.models.setting import Setting
from app.models.setting_change_history import SettingChangeHistory
from app.models.media_asset import MediaAsset
from app.models.subtitle import Subtitle
from app.models.subtitle_sync_record import SubtitleSyncRecord
from app.models.translation_memory import TranslationMemory
from app.models.translation_cache import TranslationCache
from app.models.user import User
from app.models.correction_rule import CorrectionRule
from app.models.auto_translation_rule import AutoTranslationRule
from app.models.task_log import TaskLog
from app.models.ai_provider_config import AIProviderConfig
from app.models.ai_provider_usage import AIProviderUsageLog, AIProviderQuota
from app.models.ai_model_config import AIModelConfig

__all__ = [
    "Base",
    "BaseModel",
    "BaseModelWithoutTimestamp",
    "GUID",
    "generate_uuid",
    "ModelRegistry",
    "TranslationJob",
    "Setting",
    "SettingChangeHistory",
    "MediaAsset",
    "Subtitle",
    "SubtitleSyncRecord",
    "TranslationMemory",
    "TranslationCache",
    "User",
    "CorrectionRule",
    "AutoTranslationRule",
    "TaskLog",
    "AIProviderConfig",
    "AIProviderUsageLog",
    "AIProviderQuota",
    "AIModelConfig",
]
