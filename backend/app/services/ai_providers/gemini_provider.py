"""
Google Gemini AI Provider Implementation.

Supports Google's Gemini models.
"""

from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.services.ai_providers.base import (
    AIGenerateResponse,
    AIModelInfo,
    BaseAIProvider,
)

logger = get_logger(__name__)


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini provider implementation.

    Supports Gemini Pro, Gemini Ultra, etc.
    """

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        super().__init__(
            api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL, timeout=timeout, **kwargs
        )
        if not self.api_key:
            raise ValueError("Gemini provider requires an API key")

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supports_model_pulling(self) -> bool:
        return False

    async def list_models(self) -> list[AIModelInfo]:
        """List available Gemini models."""
        known_models = [
            {
                "id": "gemini-pro",
                "name": "Gemini Pro",
                "context_length": 32768,
                "description": "Google's versatile Gemini model",
                "cost_input": 0.5,
                "cost_output": 1.5,
            },
            {
                "id": "gemini-pro-vision",
                "name": "Gemini Pro Vision",
                "context_length": 16384,
                "description": "Gemini with vision capabilities",
                "cost_input": 0.5,
                "cost_output": 1.5,
            },
            {
                "id": "gemini-ultra",
                "name": "Gemini Ultra",
                "context_length": 32768,
                "description": "Most capable Gemini model",
                "cost_input": 12.5,
                "cost_output": 37.5,
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
        """Check if a model exists in Gemini."""
        models = await self.list_models()
        return any(model.id == model_name for model in models)

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AIGenerateResponse:
        """Generate text using Gemini."""
        # Build full prompt (Gemini doesn't have separate system prompt in v1beta)
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # Extract text from response
                text = ""
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "text" in part:
                                text += part["text"]

                # Extract token counts
                usage = data.get("usageMetadata", {})

                return AIGenerateResponse(
                    text=text,
                    model=model,
                    provider=self.provider_name,
                    input_tokens=usage.get("promptTokenCount"),
                    output_tokens=usage.get("candidatesTokenCount"),
                    finish_reason=data["candidates"][0].get("finishReason")
                    if "candidates" in data
                    else None,
                )

            except httpx.HTTPError as e:
                logger.error(f"Gemini generation failed: {e}")
                if hasattr(e, "response") and e.response:
                    logger.error(f"Response: {e.response.text}")
                raise

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Generate text using Gemini with streaming."""
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/models/{model}:streamGenerateContent?key={self.api_key}",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            import json

                            data = json.loads(line)

                            if "candidates" in data and len(data["candidates"]) > 0:
                                candidate = data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            yield part["text"]

                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Failed to parse Gemini stream chunk: {e}")

            except httpx.HTTPError as e:
                logger.error(f"Gemini streaming generation failed: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
