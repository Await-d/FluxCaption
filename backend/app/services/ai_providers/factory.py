"""
AI Provider Factory and Manager.

Handles creation and management of AI providers.
"""

from app.core.logging import get_logger
from app.services.ai_providers.base import BaseAIProvider
from app.services.ai_providers.claude_provider import ClaudeProvider
from app.services.ai_providers.custom_openai_provider import CustomOpenAIProvider
from app.services.ai_providers.deepseek_provider import DeepSeekProvider
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.ai_providers.moonshot_provider import MoonshotProvider
from app.services.ai_providers.ollama_provider import OllamaProvider
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.zhipu_provider import ZhipuProvider

logger = get_logger(__name__)


class AIProviderFactory:
    """
    Factory for creating AI providers.

    Manages registration and instantiation of different AI providers.
    """

    # Registry of available providers
    _providers: dict[str, type[BaseAIProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
        "zhipu": ZhipuProvider,
        "moonshot": MoonshotProvider,
        "custom_openai": CustomOpenAIProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseAIProvider]):
        """
        Register a new AI provider.

        Args:
            name: Provider name (e.g., 'openai', 'custom')
            provider_class: Provider class that extends BaseAIProvider
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered AI provider: {name}")

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())

    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 300,
        **kwargs,
    ) -> BaseAIProvider:
        """
        Create an AI provider instance.

        Args:
            provider_name: Name of the provider (e.g., 'ollama', 'openai')
            api_key: API key for authentication (if required)
            base_url: Base URL for API
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific configuration

        Returns:
            BaseAIProvider: Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_name_lower = provider_name.lower()

        if provider_name_lower not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown AI provider: {provider_name}. Available providers: {available}"
            )

        provider_class = cls._providers[provider_name_lower]

        try:
            provider = provider_class(api_key=api_key, base_url=base_url, timeout=timeout, **kwargs)
            logger.info(f"Created {provider_name} provider instance")
            return provider

        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {e}")
            raise


class AIProviderManager:
    """
    Manages AI provider instances and configurations.

    Provides a centralized way to access configured providers.
    """

    def __init__(self):
        self._provider_cache: dict[str, BaseAIProvider] = {}

    def get_provider(
        self,
        provider_name: str,
        config: dict | None = None,
        use_cache: bool = True,
    ) -> BaseAIProvider:
        """
        Get an AI provider instance.

        Args:
            provider_name: Name of the provider
            config: Provider configuration (api_key, base_url, etc.)
            use_cache: Whether to use cached instance

        Returns:
            BaseAIProvider: Provider instance
        """
        cache_key = provider_name.lower()

        # Return cached instance if available
        if use_cache and cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

        # Create new instance
        config = config or {}
        provider = AIProviderFactory.create_provider(provider_name, **config)

        # Cache the instance
        if use_cache:
            self._provider_cache[cache_key] = provider

        return provider

    def get_provider_from_model_id(
        self,
        model_id: str,
        config: dict | None = None,
    ) -> tuple[BaseAIProvider, str]:
        """
        Get provider and model name from a model identifier.

        Args:
            model_id: Model identifier (e.g., "openai:gpt-4", "ollama:qwen2.5")
            config: Provider configuration

        Returns:
            tuple[BaseAIProvider, str]: (provider instance, model name)

        Raises:
            ValueError: If model_id format is invalid
        """
        provider_name, model_name = BaseAIProvider.parse_model_identifier(model_id)

        if not provider_name:
            raise ValueError(
                f"Invalid model identifier: {model_id}. "
                f"Expected format: 'provider:model' (e.g., 'openai:gpt-4')"
            )

        provider = self.get_provider(provider_name, config)
        return provider, model_name

    def clear_cache(self):
        """Clear all cached provider instances."""
        self._provider_cache.clear()
        logger.info("Cleared AI provider cache")

    async def health_check_all(self) -> dict[str, bool]:
        """
        Check health of all registered providers.

        Returns:
            dict[str, bool]: Provider name -> health status
        """
        results = {}

        for provider_name in AIProviderFactory.get_available_providers():
            try:
                provider = self.get_provider(provider_name, use_cache=True)
                is_healthy = await provider.health_check()
                results[provider_name] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                results[provider_name] = False

        return results


# =============================================================================
# Singleton Instance
# =============================================================================

# Global provider manager instance
provider_manager = AIProviderManager()


def get_provider_manager() -> AIProviderManager:
    """Get the global provider manager instance."""
    return provider_manager
