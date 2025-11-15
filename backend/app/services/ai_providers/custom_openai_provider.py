"""
Custom OpenAI-Compatible Provider Implementation.

Supports any OpenAI-compatible API endpoint (OpenRouter, LocalAI, vLLM, etc.).
"""

from app.services.ai_providers.openai_provider import OpenAIProvider


class CustomOpenAIProvider(OpenAIProvider):
    """
    Custom OpenAI-compatible provider implementation.

    This provider can be used with any API that implements the OpenAI API format:
    - OpenRouter (https://openrouter.ai)
    - Together AI
    - Anyscale
    - Perplexity
    - LocalAI
    - vLLM
    - Text Generation WebUI (oobabooga)
    - And many more...
    """

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        """
        Initialize custom OpenAI-compatible provider.

        Args:
            api_key: API key (may not be required for local endpoints)
            base_url: Base URL of the API endpoint (required)
            timeout: Request timeout in seconds
            **kwargs: Additional configuration
        """
        if not base_url:
            raise ValueError("Custom OpenAI provider requires a base_url")

        super().__init__(
            api_key=api_key or "dummy",  # Some endpoints don't require API key
            base_url=base_url,
            timeout=timeout,
            **kwargs,
        )

    @property
    def provider_name(self) -> str:
        return "custom_openai"

    async def check_model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists.

        For custom endpoints, we always return True since we can't reliably
        check model availability without knowing the specific API implementation.
        """
        try:
            models = await self.list_models()
            return any(model.id == model_name for model in models)
        except Exception:
            # If listing fails, assume model exists
            return True
