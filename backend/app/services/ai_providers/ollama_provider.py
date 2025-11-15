"""
Ollama AI Provider Implementation.

Adapter for existing Ollama client to implement BaseAIProvider interface.
"""

import json
from collections.abc import AsyncIterator, Callable

import httpx

from app.core.logging import get_logger
from app.services.ai_providers.base import (
    AIGenerateResponse,
    AIModelInfo,
    BaseAIProvider,
)

logger = get_logger(__name__)


class OllamaProvider(BaseAIProvider):
    """
    Ollama provider implementation.

    Wraps Ollama API to implement the standard AI provider interface.
    """

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supports_model_pulling(self) -> bool:
        return True

    async def list_models(self) -> list[AIModelInfo]:
        """List all available Ollama models."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model_data in data.get("models", []):
                    model_info = AIModelInfo(
                        id=model_data.get("name"),
                        name=model_data.get("name"),
                        provider=self.provider_name,
                        context_length=model_data.get("details", {}).get("parameter_size", 4096),
                        supports_streaming=True,
                        description=f"Ollama model: {model_data.get('name')}",
                    )
                    models.append(model_info)

                return models

            except httpx.HTTPError as e:
                logger.error(f"Failed to list Ollama models: {e}")
                raise

    async def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists locally in Ollama."""
        try:
            models = await self.list_models()
            return any(model.id == model_name for model in models)
        except Exception as e:
            logger.error(f"Error checking Ollama model existence: {e}")
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AIGenerateResponse:
        """Generate text using Ollama."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        # Add any additional Ollama-specific options
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                return AIGenerateResponse(
                    text=data.get("response", ""),
                    model=model,
                    provider=self.provider_name,
                    input_tokens=data.get("prompt_eval_count"),
                    output_tokens=data.get("eval_count"),
                    finish_reason="stop" if data.get("done") else None,
                )

            except httpx.HTTPError as e:
                logger.error(f"Ollama generation failed: {e}")
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
        """Generate text using Ollama with streaming."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk

                                if data.get("done", False):
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse Ollama stream line: {line}")

            except httpx.HTTPError as e:
                logger.error(f"Ollama streaming generation failed: {e}")
                raise

    async def pull_model(
        self,
        model_name: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> None:
        """Pull a model from Ollama registry."""
        async with httpx.AsyncClient(timeout=self.extra_config.get("pull_timeout", 3600)) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                progress_data = json.loads(line)
                                logger.debug(f"Pull progress: {progress_data}")

                                if progress_callback:
                                    progress_callback(progress_data)

                                # Check for completion
                                status = progress_data.get("status", "")
                                if "success" in status.lower() or status == "":
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse pull progress: {line}")

                logger.info(f"Successfully pulled Ollama model: {model_name}")

            except httpx.HTTPError as e:
                logger.error(f"Failed to pull Ollama model {model_name}: {e}")
                raise

    async def delete_model(self, model_name: str) -> None:
        """Delete an Ollama model."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    "DELETE",
                    f"{self.base_url}/api/delete",
                    content=json.dumps({"name": model_name}),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Successfully deleted Ollama model: {model_name}")

            except httpx.HTTPError as e:
                logger.error(f"Failed to delete Ollama model {model_name}: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
