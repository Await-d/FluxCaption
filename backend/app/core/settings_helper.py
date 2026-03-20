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
            default_model_setting = (
                db.query(Setting).filter(Setting.key == "default_mt_model").first()
            )

            if default_model_setting and default_model_setting.value:
                logger.debug(f"Using default model from database: {default_model_setting.value}")
                return default_model_setting.value
    except Exception as e:
        logger.warning(f"Failed to get default model from database: {e}, using config default")

    # Fallback to config
    logger.debug(f"Using default model from config: {settings.default_mt_model}")
    return settings.default_mt_model


def get_provider_for_model(model_name: str) -> str | None:
    """
    Get the provider name for a given model.

    Queries the AI Model Config table to find which provider owns this model.

    Args:
        model_name: Model name (e.g., "gpt-4o", "qwen2.5:7b-instruct")

    Returns:
        str | None: Provider name or None if not found
    """
    try:
        from app.core.db import SessionLocal
        from app.models.ai_model_config import AIModelConfig

        with SessionLocal() as db:
            model_config = (
                db.query(AIModelConfig)
                .filter(
                    AIModelConfig.model_name == model_name,
                    AIModelConfig.is_enabled == True,
                )
                .first()
            )

            if model_config:
                # Sanitize model name for logging (prevent log injection)
                model_name_safe = model_name.replace("\n", "\\n").replace("\r", "\\r")
                logger.debug(
                    f"Found provider '{model_config.provider_name}' for model '{model_name_safe}'"
                )
                return model_config.provider_name

            # Fallback: try to infer from model name patterns
            model_name_safe = model_name.replace("\n", "\\n").replace("\r", "\\r")
            logger.debug(f"Model '{model_name_safe}' not found in config, inferring provider")
            return _infer_provider_from_model_name(model_name)

    except Exception as e:
        model_name_safe = model_name.replace("\n", "\\n").replace("\r", "\\r")
        logger.warning(f"Failed to get provider for model '{model_name_safe}': {e}")
        return _infer_provider_from_model_name(model_name)


def _infer_provider_from_model_name(model_name: str) -> str | None:
    """
    Infer provider from model name using common patterns.

    Args:
        model_name: Model name

    Returns:
        str | None: Inferred provider name or None
    """
    model_lower = model_name.lower()

    # Provider patterns: {provider_name: {'prefixes': [...], 'contains': [...]}}
    PROVIDER_PATTERNS = {
        'openai': {'prefixes': ['gpt-'], 'contains': ['gpt']},
        'claude': {'prefixes': ['claude-'], 'contains': ['claude']},
        'gemini': {'prefixes': ['gemini-'], 'contains': ['gemini']},
        'deepseek': {'prefixes': ['deepseek-'], 'contains': ['deepseek']},
        'zhipu': {'prefixes': ['glm-'], 'contains': ['chatglm']},
        'moonshot': {'prefixes': ['moonshot-', 'kimi-'], 'contains': ['moonshot']},
        'ollama': {'prefixes': [], 'contains': ['qwen', 'llama', 'mistral']},
    }

    # Check patterns for each provider
    for provider, patterns in PROVIDER_PATTERNS.items():
        prefixes = patterns.get('prefixes', [])
        contains = patterns.get('contains', [])

        # Check if model name starts with any prefix
        if any(model_lower.startswith(p) for p in prefixes):
            return provider

        # Check if model name contains any keyword
        if any(c in model_lower for c in contains):
            return provider

    # Default to ollama if no pattern matches
    model_name_safe = model_name.replace("\n", "\\n").replace("\r", "\\r")
    logger.warning(
        f"Could not infer provider for model '{model_name_safe}', defaulting to ollama"
    )
    return "ollama"


def get_default_provider() -> str:
    """
    Get the default AI provider.

    Returns the provider of the default model, or falls back to 'ollama'.

    Returns:
        str: Default provider name
    """
    try:
        default_model = get_default_mt_model()
        provider = get_provider_for_model(default_model)

        if provider:
            logger.debug(f"Default provider for model '{default_model}': {provider}")
            return provider

        logger.warning(f"Could not determine provider for default model '{default_model}'")
        return "ollama"

    except Exception as e:
        logger.warning(f"Failed to get default provider: {e}, using 'ollama'")
        return "ollama"
