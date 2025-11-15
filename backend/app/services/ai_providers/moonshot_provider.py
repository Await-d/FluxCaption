"""
Moonshot AI (Kimi) Provider Implementation.

Supports Moonshot's Kimi models.
"""

from app.services.ai_providers.base import AIModelInfo
from app.services.ai_providers.openai_provider import OpenAIProvider


class MoonshotProvider(OpenAIProvider):
    """
    Moonshot AI (Kimi) provider implementation.

    Moonshot provides an OpenAI-compatible API for their Kimi models.
    """

    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        super().__init__(
            api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL, timeout=timeout, **kwargs
        )

    @property
    def provider_name(self) -> str:
        return "moonshot"

    async def list_models(self) -> list[AIModelInfo]:
        """List available Moonshot Kimi models."""
        known_models = [
            {
                "id": "moonshot-v1-8k",
                "name": "Kimi v1 8K",
                "context_length": 8192,
                "description": "Moonshot Kimi模型 - 8K上下文",
                "cost_input": 12.0,
                "cost_output": 12.0,
            },
            {
                "id": "moonshot-v1-32k",
                "name": "Kimi v1 32K",
                "context_length": 32768,
                "description": "Moonshot Kimi模型 - 32K上下文",
                "cost_input": 24.0,
                "cost_output": 24.0,
            },
            {
                "id": "moonshot-v1-128k",
                "name": "Kimi v1 128K",
                "context_length": 131072,
                "description": "Moonshot Kimi模型 - 128K超长上下文",
                "cost_input": 60.0,
                "cost_output": 60.0,
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
                cost_per_1k_input_tokens=model_data["cost_input"] / 1000,
                cost_per_1k_output_tokens=model_data["cost_output"] / 1000,
            )
            models.append(model_info)

        return models

    async def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists in Moonshot."""
        models = await self.list_models()
        return any(model.id == model_name for model in models)
