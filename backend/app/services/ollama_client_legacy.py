"""
Backward-compatible Ollama client wrapper.

This provides the same interface as the old ollama_client but uses
the new unified AI client system internally.
"""

from typing import Optional, Callable
from app.core.logging import get_logger
from app.services.ai_providers.ollama_provider import OllamaProvider
from app.core.config import settings

logger = get_logger(__name__)


class LegacyOllamaClient:
    """
    Backward-compatible wrapper for OllamaProvider.

    Provides the same interface as the old ollama_client but uses
    the new provider system internally.
    """

    def __init__(self):
        """Initialize legacy Ollama client."""
        self._provider: Optional[OllamaProvider] = None

    def _get_provider(self) -> OllamaProvider:
        """Get or create Ollama provider instance."""
        if self._provider is None:
            self._provider = OllamaProvider(
                base_url=settings.ollama_base_url,
                timeout=settings.ollama_timeout,
                pull_timeout=settings.ollama_pull_timeout,
            )
        return self._provider

    async def list_models(self) -> list[dict]:
        """List all available models."""
        provider = self._get_provider()
        models_info = await provider.list_models()

        # Convert to old format
        return [
            {
                "name": model.name,
                "details": {
                    "parameter_size": model.context_length,
                }
            }
            for model in models_info
        ]

    async def check_model_exists(self, model_name: str) -> bool:
        """Check if a model exists locally."""
        provider = self._get_provider()
        return await provider.check_model_exists(model_name)

    async def pull_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """Pull a model from Ollama registry with progress tracking."""
        provider = self._get_provider()
        await provider.pull_model(model_name, progress_callback)

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using a model."""
        provider = self._get_provider()
        response = await provider.generate(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.text

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """Generate text using a model with streaming response."""
        provider = self._get_provider()
        async for chunk in provider.generate_stream(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temperature,
        ):
            yield chunk

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        """Chat completion using a model."""
        # Convert messages to simple prompt
        system_msgs = [m["content"] for m in messages if m["role"] == "system"]
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]

        system = "\n".join(system_msgs) if system_msgs else None
        prompt = "\n".join(user_msgs)

        return await self.generate(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temperature,
        )

    async def delete_model(self, model_name: str) -> None:
        """Delete a model."""
        provider = self._get_provider()
        await provider.delete_model(model_name)

    async def health_check(self) -> bool:
        """Check if Ollama server is accessible."""
        provider = self._get_provider()
        return await provider.health_check()


# =============================================================================
# Singleton Instance (for backward compatibility)
# =============================================================================

ollama_client = LegacyOllamaClient()
