"""
Zhipu AI (智谱AI) GLM Provider Implementation.

Supports Zhipu's GLM models (ChatGLM, etc.).
"""

from app.services.ai_providers.base import AIModelInfo
from app.services.ai_providers.openai_provider import OpenAIProvider


class ZhipuProvider(OpenAIProvider):
    """
    Zhipu AI (智谱AI) provider implementation.

    Zhipu provides an OpenAI-compatible API for their GLM models.
    """

    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        super().__init__(
            api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL, timeout=timeout, **kwargs
        )

    @property
    def provider_name(self) -> str:
        return "zhipu"

    async def list_models(self) -> list[AIModelInfo]:
        """List available Zhipu GLM models."""
        known_models = [
            {
                "id": "glm-4",
                "name": "GLM-4",
                "context_length": 128000,
                "description": "智谱AI最新一代基座大模型GLM-4",
                "cost_input": 0.1,
                "cost_output": 0.1,
            },
            {
                "id": "glm-4-flash",
                "name": "GLM-4 Flash",
                "context_length": 128000,
                "description": "智谱AI推出的免费大模型",
                "cost_input": 0.0,
                "cost_output": 0.0,
            },
            {
                "id": "glm-3-turbo",
                "name": "GLM-3 Turbo",
                "context_length": 128000,
                "description": "适用于对知识量、推理能力、创造力要求较高的场景",
                "cost_input": 0.005,
                "cost_output": 0.005,
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
        """Check if a model exists in Zhipu."""
        models = await self.list_models()
        return any(model.id == model_name for model in models)
