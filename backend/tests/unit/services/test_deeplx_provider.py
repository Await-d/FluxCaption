import pytest
import sqlalchemy as sa
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routers.ai_providers import PROVIDER_DEFAULT_MODELS
from app.core.init_ai_providers import _ensure_deeplx_model
from app.core.settings_helper import _infer_provider_from_model_name
from app.models.ai_model_config import AIModelConfig
from app.services.unified_ai_client import UnifiedAIClient
from app.services.ai_providers.deeplx_provider import DeepLXProvider


@pytest.mark.unit
class TestDeepLXProvider:
    @pytest.mark.asyncio
    async def test_list_models_returns_translate_model(self):
        provider = DeepLXProvider(base_url="http://localhost:1188")

        models = await provider.list_models()

        assert len(models) == 1
        assert models[0].id == "translate"
        assert models[0].provider == "deeplx"

    @pytest.mark.asyncio
    async def test_check_model_exists_accepts_translate(self):
        provider = DeepLXProvider(base_url="http://localhost:1188")

        assert await provider.check_model_exists("translate") is True
        assert await provider.check_model_exists("other") is False

    def test_resolve_translate_url_from_host_only(self):
        provider = DeepLXProvider(base_url="https://trans.example.com")

        assert provider._resolve_translate_url() == "https://trans.example.com/translate"

    def test_preserve_full_translate_endpoint_with_query_token(self):
        provider = DeepLXProvider(base_url="https://trans.example.com/translate?token=123456")

        assert (
            provider._resolve_translate_url()
            == "https://trans.example.com/translate?token=123456"
        )

    def test_replace_api_key_placeholder_in_query(self):
        provider = DeepLXProvider(
            api_key="123456",
            base_url="https://trans.example.com/translate?token={{apiKey}}",
        )

        assert (
            provider._resolve_translate_url()
            == "https://trans.example.com/translate?token=123456"
        )

    def test_replace_api_key_placeholder_in_subdomain(self):
        provider = DeepLXProvider(
            api_key="123456",
            base_url="https://{{apiKey}}.trans.example.com/translate",
        )

        assert provider._resolve_translate_url() == "https://123456.trans.example.com/translate"

    def test_placeholder_requires_api_key(self):
        provider = DeepLXProvider(base_url="https://trans.example.com/translate?token={{apiKey}}")

        with pytest.raises(ValueError, match="no API key"):
            provider._resolve_translate_url()

    def test_router_default_model_mapping_contains_deeplx(self):
        assert PROVIDER_DEFAULT_MODELS["deeplx"] == "translate"

    def test_settings_helper_infers_translate_as_deeplx(self):
        assert _infer_provider_from_model_name("translate") == "deeplx"

    def test_unified_ai_client_infers_translate_as_deeplx(self):
        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = None

        client = UnifiedAIClient(session)

        assert client._infer_provider_from_model("translate") == "deeplx"

    def test_ensure_deeplx_model_creates_builtin_model(self):
        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = None

        _ensure_deeplx_model(session)

        added_model = session.add.call_args.args[0]
        assert isinstance(added_model, AIModelConfig)
        assert added_model.provider_name == "deeplx"
        assert added_model.model_name == "translate"
        assert added_model.is_default is True

    @pytest.mark.asyncio
    async def test_health_check_posts_to_translate_endpoint(self):
        provider = DeepLXProvider(base_url="https://trans.example.com/translate?token=123456")

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "ok"}
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        with patch("app.services.ai_providers.deeplx_provider.httpx.AsyncClient", return_value=mock_client):
            assert await provider.health_check() is True
            mock_client.post.assert_awaited_once()
            called_url = mock_client.post.await_args.args[0]
            assert called_url == "https://trans.example.com/translate?token=123456"
