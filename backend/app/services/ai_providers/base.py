"""
Base AI Provider Interface.

Defines the abstract interface that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass


@dataclass
class AIModelInfo:
    """Information about an AI model."""

    id: str
    name: str
    provider: str
    context_length: int
    supports_streaming: bool = True
    cost_per_1k_input_tokens: float | None = None
    cost_per_1k_output_tokens: float | None = None
    description: str | None = None


@dataclass
class AIGenerateResponse:
    """Response from AI generation."""

    text: str
    model: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI providers (Ollama, OpenAI, DeepSeek, Claude, etc.)
    must implement this interface.
    """

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        """
        Initialize AI provider.

        Args:
            api_key: API key for authentication (if required)
            base_url: Base URL for API (if customizable)
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.extra_config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name (e.g., 'ollama', 'openai', 'deepseek')."""
        pass

    @property
    @abstractmethod
    def supports_model_pulling(self) -> bool:
        """Whether this provider supports pulling/downloading models."""
        pass

    @abstractmethod
    async def list_models(self) -> list[AIModelInfo]:
        """
        List all available models.

        Returns:
            list[AIModelInfo]: List of available models

        Raises:
            Exception: If listing models fails
        """
        pass

    @abstractmethod
    async def check_model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists/is available.

        Args:
            model_name: Name of the model to check

        Returns:
            bool: True if model exists, False otherwise
        """
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AIGenerateResponse:
        """
        Generate text using a model.

        Args:
            model: Model name to use
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            AIGenerateResponse: Generated response with metadata

        Raises:
            Exception: If generation fails
        """
        pass

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Generate text using a model with streaming response.

        Args:
            model: Model name to use
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            str: Generated text chunks

        Raises:
            Exception: If streaming generation fails
        """
        # Default implementation: non-streaming (providers should override if supported)
        response = await self.generate(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield response.text

    async def pull_model(
        self,
        model_name: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> None:
        """
        Pull/download a model (only for providers that support it).

        Args:
            model_name: Name of the model to pull
            progress_callback: Optional callback for progress updates

        Raises:
            NotImplementedError: If provider doesn't support model pulling
        """
        raise NotImplementedError(f"{self.provider_name} does not support model pulling")

    async def delete_model(self, model_name: str) -> None:
        """
        Delete a model (only for providers that support it).

        Args:
            model_name: Name of the model to delete

        Raises:
            NotImplementedError: If provider doesn't support model deletion
        """
        raise NotImplementedError(f"{self.provider_name} does not support model deletion")

    async def health_check(self) -> bool:
        """
        Check if the provider is accessible/healthy.

        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            await self.list_models()
            return True
        except Exception:
            return False

    def get_model_identifier(self, model_name: str) -> str:
        """
        Get the fully qualified model identifier.

        Args:
            model_name: Model name

        Returns:
            str: Fully qualified identifier (e.g., "openai:gpt-4", "ollama:qwen2.5")
        """
        return f"{self.provider_name}:{model_name}"

    @classmethod
    def parse_model_identifier(cls, identifier: str) -> tuple[str, str]:
        """
        Parse a fully qualified model identifier.

        Args:
            identifier: Identifier (e.g., "openai:gpt-4" or just "gpt-4")

        Returns:
            tuple[str, str]: (provider_name, model_name)
        """
        if ":" in identifier:
            provider, model = identifier.split(":", 1)
            return provider, model
        else:
            # No provider specified, assume it's just the model name
            return "", identifier
