"""
DeepSeek AI Provider Implementation.

DeepSeek uses OpenAI-compatible API, so we inherit from OpenAIProvider.
"""

from typing import Optional
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.base import AIModelInfo


class DeepSeekProvider(OpenAIProvider):
    """
    DeepSeek provider implementation.

    DeepSeek provides an OpenAI-compatible API, so we inherit most functionality
    from OpenAIProvider and only override provider-specific details.
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 300,
        **kwargs
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            timeout=timeout,
            **kwargs
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def list_models(self) -> list[AIModelInfo]:
        """
        List available DeepSeek models.

        Since DeepSeek has a fixed set of models, we can hardcode them
        or call the parent's list_models and filter.
        """
        # DeepSeek's known models (as of 2025)
        known_models = [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "context_length": 32768,
                "description": "DeepSeek's flagship chat model",
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek Coder",
                "context_length": 16384,
                "description": "DeepSeek's code-specialized model",
            },
        ]

        models = []
        for model_data in known_models:
            model_info = AIModelInfo(
                id=model_data["id"],
                name=model_data["name"],
                provider=self.provider_name,
                context_length=model_data["context_length"],
                supports_streaming=True,
                description=model_data["description"],
                cost_per_1k_input_tokens=0.14,  # DeepSeek pricing (as of 2025)
                cost_per_1k_output_tokens=0.28,
            )
            models.append(model_info)

        return models

    async def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists in DeepSeek."""
        models = await self.list_models()
        return any(model.id == model_name for model in models)
