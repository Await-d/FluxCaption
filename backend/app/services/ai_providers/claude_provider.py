"""
Claude (Anthropic) AI Provider Implementation.

Supports Anthropic's Claude API.
"""

from collections.abc import AsyncIterator

import httpx

from app.core.logging import get_logger
from app.services.ai_providers.base import (
    AIGenerateResponse,
    AIModelInfo,
    BaseAIProvider,
)
from app.services.ai_response_cleaner import ReasoningBlockFilter, extract_visible_text

logger = get_logger(__name__)


def _log_http_error(message: str, error: httpx.HTTPError) -> None:
    if hasattr(error, "response") and error.response:
        logger.error(f"{message} with status {error.response.status_code}")
    else:
        logger.error(f"{message}: {type(error).__name__}")


class ClaudeProvider(BaseAIProvider):
    """
    Claude (Anthropic) provider implementation.

    Supports Claude API (Sonnet, Opus, Haiku).
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        super().__init__(
            api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL, timeout=timeout, **kwargs
        )
        if not self.api_key:
            raise ValueError("Claude provider requires an API key")

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def supports_model_pulling(self) -> bool:
        return False

    def _get_headers(self) -> dict:
        """Get headers for Claude API requests."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[AIModelInfo]:
        """
        List available Claude models.

        Anthropic doesn't provide a models endpoint, so we return known models.
        """
        known_models = [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_length": 200000,
                "description": "Most powerful Claude model",
                "cost_input": 15.0,
                "cost_output": 75.0,
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_length": 200000,
                "description": "Balanced performance and speed",
                "cost_input": 3.0,
                "cost_output": 15.0,
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_length": 200000,
                "description": "Fastest and most compact",
                "cost_input": 0.25,
                "cost_output": 1.25,
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "context_length": 200000,
                "description": "Latest Sonnet model with improved capabilities",
                "cost_input": 3.0,
                "cost_output": 15.0,
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
        """Check if a model exists in Claude."""
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
        """Generate text using Claude."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        # Add any additional Claude-specific parameters
        for key in ["top_p", "top_k", "stop_sequences"]:
            if key in kwargs:
                payload[key] = kwargs[key]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                usage = data.get("usage", {})

                return AIGenerateResponse(
                    text=extract_visible_text(data.get("content", [])),
                    model=data.get("model", model),
                    provider=self.provider_name,
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    finish_reason=data.get("stop_reason"),
                )

            except httpx.HTTPError as e:
                _log_http_error("Claude generation failed", e)
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
        """Generate text using Claude with streaming."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }

        if system:
            payload["system"] = system

        reasoning_filter = ReasoningBlockFilter()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("event: "):
                            continue

                        if line.startswith("data: "):
                            line = line[6:]  # Remove "data: " prefix

                        if line == "[DONE]":
                            break

                        try:
                            import json

                            data = json.loads(line)

                            visible_text = reasoning_filter.filter(extract_visible_text(data))
                            if visible_text:
                                yield visible_text

                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Failed to parse Claude stream chunk: {e}")

                    pending_text = reasoning_filter.flush()
                    if pending_text:
                        yield pending_text

            except httpx.HTTPError as e:
                _log_http_error("Claude streaming generation failed", e)
                raise

    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        try:
            # Try to list models (which is just returning hardcoded list)
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Claude health check failed: {type(e).__name__}")
            return False
