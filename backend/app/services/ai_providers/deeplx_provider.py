"""
DeepLX provider implementation.

DeepLX exposes a translation-focused HTTP API rather than an LLM chat API.
"""

from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.core.logging import get_logger
from app.services.ai_providers.base import AIGenerateResponse, AIModelInfo, BaseAIProvider

logger = get_logger(__name__)


class DeepLXProvider(BaseAIProvider):
    """DeepLX translation provider."""

    DEFAULT_BASE_URL = "http://localhost:1188"
    DEFAULT_MODEL = "translate"

    def __init__(
        self, api_key: str | None = None, base_url: str | None = None, timeout: int = 300, **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url or self.DEFAULT_BASE_URL, timeout=timeout, **kwargs)

    @property
    def provider_name(self) -> str:
        return "deeplx"

    @property
    def supports_model_pulling(self) -> bool:
        return False

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _resolve_base_url_template(self) -> str:
        base_url = (self.base_url or self.DEFAULT_BASE_URL).strip()
        if "{{apiKey}}" in base_url:
            if not self.api_key:
                raise ValueError("DeepLX base_url contains {{apiKey}} but no API key was provided")
            return base_url.replace("{{apiKey}}", quote(self.api_key, safe=""))
        return base_url

    def _resolve_translate_url(self) -> str:
        base_url = self._resolve_base_url_template()
        parts = urlsplit(base_url)
        path = parts.path.rstrip("/")

        if path.endswith("/translate") or path.endswith("/v1/translate") or path.endswith("/v2/translate"):
            return urlunsplit(parts)

        resolved_path = f"{path}/translate" if path else "/translate"
        return urlunsplit((parts.scheme, parts.netloc, resolved_path, parts.query, parts.fragment))

    async def list_models(self) -> list[AIModelInfo]:
        return [
            AIModelInfo(
                id=self.DEFAULT_MODEL,
                name="DeepLX Translate",
                provider=self.provider_name,
                context_length=0,
                supports_streaming=False,
                description="DeepLX translation endpoint",
                cost_per_1k_input_tokens=0.0,
                cost_per_1k_output_tokens=0.0,
            )
        ]

    async def check_model_exists(self, model_name: str) -> bool:
        return model_name in {self.DEFAULT_MODEL, "", None}

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AIGenerateResponse:
        source_lang = kwargs.get("source_lang")
        target_lang = kwargs.get("target_lang")

        if not prompt:
            raise ValueError("DeepLX provider requires non-empty text")
        if not target_lang:
            raise ValueError("DeepLX provider requires target_lang")

        payload = {
            "text": prompt,
            "target_lang": target_lang.upper(),
        }
        if source_lang:
            payload["source_lang"] = source_lang.upper()

        translate_url = self._resolve_translate_url()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    translate_url,
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as e:
                logger.error(f"DeepLX generation failed: {e}")
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                raise

        translated_text = data.get("data")
        if not isinstance(translated_text, str) or not translated_text.strip():
            raise ValueError("DeepLX returned an empty translation")

        return AIGenerateResponse(
            text=translated_text.strip(),
            model=self.DEFAULT_MODEL,
            provider=self.provider_name,
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 10)) as client:
                response = await client.post(
                    self._resolve_translate_url(),
                    headers=self._get_headers(),
                    json={"text": "health", "target_lang": "EN"},
                )
                response.raise_for_status()
                data = response.json()
                translated_text = data.get("data")
                return isinstance(translated_text, str) and bool(translated_text.strip())
        except Exception as e:
            logger.error(f"DeepLX health check failed: {e}")
            return False
