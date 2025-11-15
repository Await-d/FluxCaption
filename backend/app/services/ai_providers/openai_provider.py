"""
OpenAI AI Provider Implementation.

Supports OpenAI API and compatible providers (OpenRouter, etc.).
"""

from typing import Optional, AsyncIterator
import httpx

from app.core.logging import get_logger
from app.services.ai_providers.base import (
    BaseAIProvider,
    AIModelInfo,
    AIGenerateResponse,
)

logger = get_logger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI provider implementation.

    Supports official OpenAI API and compatible endpoints.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"

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
        if not self.api_key:
            raise ValueError("OpenAI provider requires an API key")

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supports_model_pulling(self) -> bool:
        return False

    def _get_headers(self) -> dict:
        """Get headers for OpenAI API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[AIModelInfo]:
        """List available OpenAI models."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("data", []):
                    # Filter for chat models (gpt-3.5, gpt-4, etc.)
                    model_id = model_data.get("id", "")
                    if not any(prefix in model_id for prefix in ["gpt-", "o1-", "o3-"]):
                        continue

                    # Estimate context length based on model name
                    context_length = 4096  # Default
                    if "gpt-4" in model_id:
                        if "32k" in model_id:
                            context_length = 32768
                        elif "turbo" in model_id or "0125" in model_id:
                            context_length = 128000
                        else:
                            context_length = 8192
                    elif "gpt-3.5" in model_id:
                        if "16k" in model_id:
                            context_length = 16384
                        else:
                            context_length = 4096

                    model_info = AIModelInfo(
                        id=model_id,
                        name=model_id,
                        provider=self.provider_name,
                        context_length=context_length,
                        supports_streaming=True,
                        description=f"OpenAI model: {model_id}",
                    )
                    models.append(model_info)

                return models

            except httpx.HTTPError as e:
                logger.error(f"Failed to list OpenAI models: {e}")
                raise

    async def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists in OpenAI."""
        try:
            models = await self.list_models()
            return any(model.id == model_name for model in models)
        except Exception:
            # If listing fails, assume model exists (OpenAI handles validation)
            return True

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AIGenerateResponse:
        """Generate text using OpenAI."""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Add any additional OpenAI-specific parameters
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
            if key in kwargs:
                payload[key] = kwargs[key]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                choice = data["choices"][0]
                usage = data.get("usage", {})

                return AIGenerateResponse(
                    text=choice["message"]["content"],
                    model=data.get("model", model),
                    provider=self.provider_name,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    finish_reason=choice.get("finish_reason"),
                )

            except httpx.HTTPError as e:
                logger.error(f"OpenAI generation failed: {e}")
                if hasattr(e, "response") and e.response:
                    logger.error(f"Response: {e.response.text}")
                raise

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Generate text using OpenAI with streaming."""
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("data: "):
                            line = line[6:]  # Remove "data: " prefix

                        if line == "[DONE]":
                            break

                        try:
                            import json
                            data = json.loads(line)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content")

                            if content:
                                yield content

                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            logger.warning(f"Failed to parse OpenAI stream chunk: {e}")

            except httpx.HTTPError as e:
                logger.error(f"OpenAI streaming generation failed: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
