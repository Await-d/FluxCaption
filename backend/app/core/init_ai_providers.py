"""
AI Provider Initialization Service.

Automatically initializes AI provider configurations from environment variables.
"""

import json
from typing import Optional
from sqlalchemy.orm import Session
import sqlalchemy as sa

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai_provider_config import AIProviderConfig
from app.models.ai_provider_usage import AIProviderQuota

logger = get_logger(__name__)


def init_ai_providers(session: Session) -> None:
    """
    Initialize AI provider configurations from environment variables.

    This function checks for API keys in environment and creates/updates
    provider configurations accordingly.

    Args:
        session: Database session
    """
    logger.info("Initializing AI provider configurations...")

    # Define provider configurations
    providers = [
        {
            "provider_name": "ollama",
            "display_name": "Ollama (Local)",
            "is_enabled": True,  # Always enable Ollama
            "api_key": None,
            "base_url": settings.ollama_base_url,
            "timeout": settings.ollama_timeout,
            "default_model": settings.default_mt_model,
            "priority": 1,
            "description": "Local LLM deployment with Ollama - Free and privacy-friendly",
            "quota": None,  # No quota for local deployment
        },
        {
            "provider_name": "openai",
            "display_name": "OpenAI",
            "is_enabled": bool(settings.openai_api_key),
            "api_key": settings.openai_api_key,
            "base_url": "https://api.openai.com/v1",
            "timeout": 300,
            "default_model": "gpt-3.5-turbo",
            "priority": 2,
            "description": "OpenAI GPT models (GPT-4, GPT-3.5, etc.)",
            "quota": {"daily_limit": 10.0, "monthly_limit": 100.0},
        },
        {
            "provider_name": "deepseek",
            "display_name": "DeepSeek",
            "is_enabled": bool(settings.deepseek_api_key),
            "api_key": settings.deepseek_api_key,
            "base_url": "https://api.deepseek.com/v1",
            "timeout": 300,
            "default_model": "deepseek-chat",
            "priority": 3,
            "description": "DeepSeek AI models - Affordable and powerful",
            "quota": {"daily_limit": 5.0, "monthly_limit": 50.0},
        },
        {
            "provider_name": "claude",
            "display_name": "Claude (Anthropic)",
            "is_enabled": bool(settings.claude_api_key),
            "api_key": settings.claude_api_key,
            "base_url": "https://api.anthropic.com/v1",
            "timeout": 300,
            "default_model": "claude-3-5-sonnet-20241022",
            "priority": 4,
            "description": "Anthropic Claude models (Opus, Sonnet, Haiku)",
            "quota": {"daily_limit": 20.0, "monthly_limit": 200.0},
        },
        {
            "provider_name": "gemini",
            "display_name": "Gemini (Google)",
            "is_enabled": bool(settings.gemini_api_key),
            "api_key": settings.gemini_api_key,
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "timeout": 300,
            "default_model": "gemini-pro",
            "priority": 5,
            "description": "Google Gemini models",
            "quota": {"daily_limit": 10.0, "monthly_limit": 100.0},
        },
        {
            "provider_name": "zhipu",
            "display_name": "智谱AI (GLM)",
            "is_enabled": bool(settings.zhipu_api_key),
            "api_key": settings.zhipu_api_key,
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "timeout": 300,
            "default_model": "glm-4",
            "priority": 6,
            "description": "智谱AI GLM models - Chinese-optimized",
            "quota": {"daily_limit": 5.0, "monthly_limit": 50.0},
        },
        {
            "provider_name": "moonshot",
            "display_name": "Moonshot AI (Kimi)",
            "is_enabled": bool(settings.moonshot_api_key),
            "api_key": settings.moonshot_api_key,
            "base_url": "https://api.moonshot.cn/v1",
            "timeout": 300,
            "default_model": "moonshot-v1-32k",
            "priority": 7,
            "description": "Moonshot Kimi models - Super long context",
            "quota": {"daily_limit": 10.0, "monthly_limit": 100.0},
        },
        {
            "provider_name": "custom_openai",
            "display_name": "Custom OpenAI Compatible",
            "is_enabled": bool(settings.custom_openai_api_key and settings.custom_openai_base_url),
            "api_key": settings.custom_openai_api_key,
            "base_url": settings.custom_openai_base_url,
            "timeout": 300,
            "default_model": None,
            "priority": 8,
            "description": "Custom OpenAI-compatible endpoint (OpenRouter, LocalAI, vLLM, etc.)",
            "quota": {"daily_limit": 10.0, "monthly_limit": 100.0},
        },
    ]

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for provider_data in providers:
        provider_name = provider_data["provider_name"]

        # Check if exists
        stmt = sa.select(AIProviderConfig).where(
            AIProviderConfig.provider_name == provider_name
        )
        existing = session.execute(stmt).scalar_one_or_none()

        if existing:
            # Only update if API key is provided and different, or if it's Ollama
            should_update = False

            if provider_name == "ollama":
                # Always update Ollama config
                should_update = True
            elif provider_data["api_key"] and existing.api_key != provider_data["api_key"]:
                # Update if API key changed
                should_update = True

            if should_update:
                existing.display_name = provider_data["display_name"]
                existing.is_enabled = provider_data["is_enabled"]
                if provider_data["api_key"]:
                    existing.api_key = provider_data["api_key"]
                if provider_data["base_url"]:
                    existing.base_url = provider_data["base_url"]
                existing.timeout = provider_data["timeout"]
                existing.default_model = provider_data["default_model"]
                existing.priority = provider_data["priority"]
                existing.description = provider_data["description"]

                updated_count += 1
                logger.info(f"Updated provider config: {provider_name}")
            else:
                skipped_count += 1
        else:
            # Create new provider config
            new_config = AIProviderConfig(
                provider_name=provider_data["provider_name"],
                display_name=provider_data["display_name"],
                is_enabled=provider_data["is_enabled"],
                api_key=provider_data["api_key"],
                base_url=provider_data["base_url"],
                timeout=provider_data["timeout"],
                default_model=provider_data["default_model"],
                priority=provider_data["priority"],
                description=provider_data["description"],
            )
            session.add(new_config)
            created_count += 1
            logger.info(f"Created provider config: {provider_name}")

        # Initialize quota for cloud providers
        if provider_data["quota"] and provider_name != "ollama":
            _init_provider_quota(session, provider_name, provider_data["quota"])

    session.commit()

    logger.info(
        f"AI provider initialization complete: "
        f"{created_count} created, {updated_count} updated, {skipped_count} skipped"
    )


def _init_provider_quota(
    session: Session,
    provider_name: str,
    quota_config: dict,
) -> None:
    """
    Initialize quota configuration for a provider.

    Args:
        session: Database session
        provider_name: Provider name
        quota_config: Quota configuration dict
    """
    from datetime import datetime, timezone

    # Check if quota exists
    stmt = sa.select(AIProviderQuota).where(
        AIProviderQuota.provider_name == provider_name
    )
    existing_quota = session.execute(stmt).scalar_one_or_none()

    if not existing_quota:
        # Create new quota
        quota = AIProviderQuota(
            provider_name=provider_name,
            daily_limit=quota_config.get("daily_limit"),
            monthly_limit=quota_config.get("monthly_limit"),
            daily_token_limit=quota_config.get("daily_token_limit"),
            monthly_token_limit=quota_config.get("monthly_token_limit"),
            alert_threshold_percent=80,
            auto_disable_on_limit=True,
            daily_reset_at=datetime.now(timezone.utc),
            monthly_reset_at=datetime.now(timezone.utc),
        )
        session.add(quota)
        logger.info(
            f"Created quota for {provider_name}: "
            f"${quota_config.get('daily_limit')}/day, "
            f"${quota_config.get('monthly_limit')}/month"
        )
