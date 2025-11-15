"""
Unified AI Client Service.

Provides a single interface for all AI operations, abstracting provider selection.
"""

import json
import time
from typing import Optional
from sqlalchemy.orm import Session
import sqlalchemy as sa

from app.core.logging import get_logger
from app.services.ai_providers.factory import provider_manager
from app.services.ai_providers.base import BaseAIProvider, AIGenerateResponse
from app.services.ai_quota_service import AIQuotaService, QuotaExceededException
from app.models.ai_provider_config import AIProviderConfig
from app.models.model_registry import ModelRegistry

logger = get_logger(__name__)


class UnifiedAIClient:
    """
    Unified AI client that works with all providers.

    Automatically selects the correct provider based on model identifier
    and manages provider configurations from database.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize unified AI client.

        Args:
            session: Optional database session for loading configs
        """
        self.session = session
        self._provider_configs = {}
        self.quota_service = AIQuotaService(session) if session else None

    def _load_provider_config(self, provider_name: str) -> dict:
        """
        Load provider configuration from database.

        Args:
            provider_name: Name of the provider

        Returns:
            dict: Provider configuration

        Raises:
            ValueError: If provider is not configured or not enabled
        """
        if provider_name in self._provider_configs:
            return self._provider_configs[provider_name]

        if not self.session:
            # No database session, return empty config (will use env vars/defaults)
            return {}

        # Load from database
        stmt = sa.select(AIProviderConfig).where(
            AIProviderConfig.provider_name == provider_name
        )
        config_record = self.session.execute(stmt).scalar_one_or_none()

        if not config_record:
            # Provider not in database, use defaults
            logger.warning(f"Provider {provider_name} not configured in database")
            return {}

        if not config_record.is_enabled:
            raise ValueError(f"Provider {provider_name} is disabled")

        # Build config dict
        config = {
            "api_key": config_record.api_key,
            "base_url": config_record.base_url,
            "timeout": config_record.timeout,
        }

        # Parse extra config
        if config_record.extra_config:
            try:
                extra = json.loads(config_record.extra_config)
                config.update(extra)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse extra_config for {provider_name}")

        # Cache the config
        self._provider_configs[provider_name] = config

        return config

    def get_provider(self, provider_name: str) -> BaseAIProvider:
        """
        Get a provider instance with configuration from database.

        Args:
            provider_name: Name of the provider (e.g., "ollama", "openai", "deepseek")

        Returns:
            BaseAIProvider: Configured provider instance

        Raises:
            ValueError: If provider is not configured or disabled
            KeyError: If provider name is not registered
        """
        config = self._load_provider_config(provider_name)
        return provider_manager.get_provider(provider_name, config=config)

    def get_provider_from_model(self, model_id: str) -> tuple[BaseAIProvider, str]:
        """
        Get provider and model name from model identifier.

        Parses model identifiers in the format "provider:model_name" (e.g., "openai:gpt-4").
        If no provider prefix is found, attempts to infer from database registry.

        Args:
            model_id: Model identifier (e.g., "openai:gpt-4", "ollama:qwen2.5", or just "gpt-4")

        Returns:
            tuple[BaseAIProvider, str]: (provider instance, model_name)

        Raises:
            ValueError: If provider cannot be inferred and no provider prefix specified
        """
        provider_name, model_name = BaseAIProvider.parse_model_identifier(model_id)

        if not provider_name:
            # No provider specified, try to infer from database
            provider_name = self._infer_provider_from_model(model_name)

        provider = self.get_provider(provider_name)
        return provider, model_name

    def _infer_provider_from_model(self, model_name: str) -> str:
        """
        Infer provider from model name by checking model registry.

        Args:
            model_name: Model name

        Returns:
            str: Provider name

        Raises:
            ValueError: If provider cannot be inferred
        """
        if not self.session:
            raise ValueError(
                f"Cannot infer provider for model {model_name} without database session"
            )

        # Check model registry
        stmt = sa.select(ModelRegistry).where(ModelRegistry.name == model_name)
        model_record = self.session.execute(stmt).scalar_one_or_none()

        if model_record:
            return model_record.provider

        # Fallback: try to guess based on model name patterns
        if model_name.startswith("gpt-") or model_name.startswith("o1-"):
            return "openai"
        elif "deepseek" in model_name.lower():
            return "deepseek"
        elif "claude" in model_name.lower():
            return "claude"
        else:
            # Default to ollama for unknown models
            return "ollama"

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the specified model.

        Args:
            model: Model identifier (e.g., "openai:gpt-4" or just "gpt-4")
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            provider: Optional provider name to use (auto-selects if not specified)
            job_id: Optional job ID for tracking
            user_id: Optional user ID for tracking
            **kwargs: Additional provider-specific parameters

        Returns:
            str: Generated text response

        Raises:
            QuotaExceededException: If quota limit is exceeded
            ValueError: If provider selection fails
            RuntimeError: If all providers fail
        """
        # If provider is explicitly specified, use it
        if provider:
            try:
                provider_instance = self.get_provider(provider)
                model_name = model  # Use model as-is when provider is specified
            except Exception as e:
                logger.error(f"Failed to get provider {provider}: {e}")
                raise ValueError(f"Invalid provider: {provider}") from e
        else:
            # Auto-select provider from model identifier
            provider_instance, model_name = self.get_provider_from_model(model)

        # Check quota before making request (for cloud providers only)
        if self.quota_service and provider_instance.provider_name != "ollama":
            try:
                self.quota_service.check_quota(provider_instance.provider_name)
            except QuotaExceededException as e:
                logger.error(f"Quota exceeded for {provider_instance.provider_name}: {e}")
                # Log the failed attempt
                if self.session:
                    self.quota_service.log_error(
                        provider_name=provider_instance.provider_name,
                        model_name=model_name,
                        error_message=str(e),
                        request_type="generate",
                        job_id=job_id,
                        user_id=user_id,
                    )
                    self.session.commit()
                raise

        logger.info(
            f"Generating with {provider_instance.provider_name}:{model_name} "
            f"(temp={temperature}, max_tokens={max_tokens})"
        )

        # Track response time
        start_time = time.time()

        try:
            response = await provider_instance.generate(
                model=model_name,
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # Log usage for cloud providers
            if self.quota_service and provider_instance.provider_name != "ollama":
                try:
                    self.quota_service.log_usage(
                        provider_name=provider_instance.provider_name,
                        model_name=model_name,
                        response=response,
                        request_type="generate",
                        job_id=job_id,
                        user_id=user_id,
                        prompt_preview=prompt[:200] if prompt else None,
                        response_preview=response.text[:200] if response.text else None,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_time_ms=response_time_ms,
                    )
                    self.session.commit()
                except Exception as log_error:
                    logger.warning(f"Failed to log usage: {log_error}")
                    # Don't fail the request if logging fails
                    if self.session:
                        self.session.rollback()

            # Return text response
            return response.text if hasattr(response, 'text') else str(response)

        except Exception as e:
            logger.error(
                f"Generation failed with {provider_instance.provider_name}:{model_name}: {e}",
                exc_info=True
            )

            # Log the error if quota service is available
            if self.quota_service and provider_instance.provider_name != "ollama":
                try:
                    self.quota_service.log_error(
                        provider_name=provider_instance.provider_name,
                        model_name=model_name,
                        error_message=str(e),
                        request_type="generate",
                        job_id=job_id,
                        user_id=user_id,
                    )
                    if self.session:
                        self.session.commit()
                except Exception as log_error:
                    logger.warning(f"Failed to log error: {log_error}")

            raise RuntimeError(
                f"Translation failed using {provider_instance.provider_name}:{model_name} - {str(e)}"
            ) from e

    def _update_model_usage(self, provider: str, model_name: str):
        """Update model usage statistics in database."""
        try:
            from datetime import datetime, timezone

            stmt = sa.select(ModelRegistry).where(
                ModelRegistry.provider == provider,
                ModelRegistry.name == model_name
            )
            model_record = self.session.execute(stmt).scalar_one_or_none()

            if model_record:
                model_record.usage_count += 1
                model_record.last_used = datetime.now(timezone.utc)
                self.session.commit()

        except Exception as e:
            logger.warning(f"Failed to update model usage stats: {e}")

    async def list_models(self, provider_name: Optional[str] = None) -> list:
        """
        List available models.

        Args:
            provider_name: Optional provider name to filter by

        Returns:
            list: List of model information
        """
        if provider_name:
            # List models for specific provider
            provider = self.get_provider(provider_name)
            return await provider.list_models()
        else:
            # List models for all enabled providers
            if not self.session:
                return []

            models = []
            stmt = sa.select(AIProviderConfig).where(
                AIProviderConfig.is_enabled == True
            ).order_by(AIProviderConfig.priority)

            for config in self.session.execute(stmt).scalars():
                try:
                    provider = self.get_provider(config.provider_name)
                    provider_models = await provider.list_models()
                    models.extend(provider_models)
                except Exception as e:
                    logger.error(f"Failed to list models for {config.provider_name}: {e}")

            return models

    async def check_model_exists(self, model_id: str) -> bool:
        """
        Check if a model exists and is accessible.

        Args:
            model_id: Model identifier (e.g., "openai:gpt-4" or "ollama:qwen2.5")

        Returns:
            bool: True if model exists and is accessible, False otherwise

        Note:
            Does not raise exceptions - returns False if provider or model cannot be found
        """
        try:
            provider, model_name = self.get_provider_from_model(model_id)
            return await provider.check_model_exists(model_name)
        except Exception as e:
            logger.error(f"Failed to check model existence: {e}")
            return False


# =============================================================================
# Helper function for backward compatibility
# =============================================================================

def get_unified_ai_client(session: Optional[Session] = None) -> UnifiedAIClient:
    """
    Get a unified AI client instance.

    Args:
        session: Optional database session

    Returns:
        UnifiedAIClient: Client instance
    """
    return UnifiedAIClient(session=session)
