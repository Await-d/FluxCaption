"""
Ollama API client for model management and inference.

Handles communication with Ollama server for model pulling and text generation.
"""

import json
from collections.abc import AsyncIterator, Callable

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_response_cleaner import ReasoningBlockFilter, extract_visible_text

logger = get_logger(__name__)


def _log_http_error(message: str, error: httpx.HTTPError) -> None:
    if hasattr(error, "response") and error.response:
        logger.error(f"{message} with status {error.response.status_code}")
    else:
        logger.error(f"{message}: {type(error).__name__}")


class OllamaClient:
    """
    Client for interacting with Ollama API.

    Provides methods for:
    - Listing available models
    - Pulling models with progress tracking
    - Generating text (translation)
    - Checking model availability
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama API base URL (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.ollama_timeout
        self.keep_alive = settings.ollama_keep_alive

    async def list_models(self) -> list[dict]:
        """
        List all available models.

        Returns:
            list[dict]: List of model information dictionaries

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
            except httpx.HTTPError as e:
                _log_http_error("Failed to list models", e)
                raise

    async def check_model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists locally.

        Args:
            model_name: Name of the model to check

        Returns:
            bool: True if model exists, False otherwise
        """
        try:
            models = await self.list_models()
            return any(model.get("name") == model_name for model in models)
        except Exception as e:
            logger.error(f"Error checking model existence: {type(e).__name__}")
            return False

    async def pull_model(
        self,
        model_name: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> None:
        """
        Pull a model from Ollama registry with progress tracking.

        Args:
            model_name: Name of the model to pull
            progress_callback: Optional callback for progress updates

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=settings.ollama_pull_timeout) as client:
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
                                logger.warning(f"Failed to parse progress line: {line}")

                logger.info(f"Successfully pulled model: {model_name}")

            except httpx.HTTPError as e:
                _log_http_error(f"Failed to pull model {model_name}", e)
                raise

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate text using a model.

        Args:
            model: Model name to use
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            str: Generated text

        Raises:
            httpx.HTTPError: If the request fails
        """
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

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return extract_visible_text(data)

            except httpx.HTTPError as e:
                _log_http_error("Generation failed", e)
                raise

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Generate text using a model with streaming response.

        Args:
            model: Model name to use
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature

        Yields:
            str: Generated text chunks

        Raises:
            httpx.HTTPError: If the request fails
        """
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

        reasoning_filter = ReasoningBlockFilter()

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
                                visible_chunk = reasoning_filter.filter(extract_visible_text(data))
                                if visible_chunk:
                                    yield visible_chunk

                                if data.get("done", False):
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse stream line: {line}")

                    pending_chunk = reasoning_filter.flush()
                    if pending_chunk:
                        yield pending_chunk

            except httpx.HTTPError as e:
                _log_http_error("Streaming generation failed", e)
                raise

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        """
        Chat completion using a model.

        Args:
            model: Model name to use
            messages: Chat messages (list of {role, content} dicts)
            temperature: Sampling temperature

        Returns:
            str: Generated response

        Raises:
            httpx.HTTPError: If the request fails
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return extract_visible_text(data)

            except httpx.HTTPError as e:
                _log_http_error("Chat completion failed", e)
                raise

    async def delete_model(self, model_name: str) -> None:
        """
        Delete a model.

        Args:
            model_name: Name of the model to delete

        Raises:
            httpx.HTTPError: If the request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    "DELETE",
                    f"{self.base_url}/api/delete",
                    content=json.dumps({"name": model_name}),
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Successfully deleted model: {model_name}")

            except httpx.HTTPError as e:
                _log_http_error(f"Failed to delete model {model_name}", e)
                raise

    async def health_check(self, log_errors: bool = True) -> bool:
        """
        Check if Ollama server is accessible.

        Returns:
            bool: True if server is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception as e:
            if log_errors:
                logger.error(f"Ollama health check failed: {type(e).__name__}")
            return False


# =============================================================================
# Singleton Instance
# =============================================================================

ollama_client = OllamaClient()
