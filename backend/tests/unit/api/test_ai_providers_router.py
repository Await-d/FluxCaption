from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.ai_providers import router
from app.core.db import get_db
from app.services.ai_providers.base import AIGenerateResponse


def make_provider_config_record(**overrides):
    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "provider_name": "ollama",
        "display_name": "Ollama",
        "is_enabled": False,
        "api_key": None,
        "base_url": "http://localhost:11434",
        "timeout": 300,
        "extra_config": None,
        "default_model": "qwen2.5:7b-instruct",
        "last_health_check": None,
        "is_healthy": False,
        "health_error": None,
        "priority": 0,
        "description": None,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def provider_db_session():
    session = MagicMock()
    config_record = make_provider_config_record()
    session.execute.return_value.scalar_one_or_none.return_value = config_record
    return session


@pytest.fixture
def provider_test_client(provider_db_session):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: provider_db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.unit
def test_pull_provider_model_calls_supported_provider(provider_test_client, provider_db_session):
    provider = SimpleNamespace(
        supports_model_pulling=True,
        pull_model=AsyncMock(),
        delete_model=AsyncMock(),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ) as mock_get_provider:
        response = provider_test_client.post(
            "/api/ai-providers/ollama/models/pull",
            json={"name": "qwen2.5:7b-instruct", "insecure": False},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "pulled"
    provider.pull_model.assert_awaited_once_with("qwen2.5:7b-instruct")
    mock_get_provider.assert_called_once()
    provider_db_session.execute.assert_called_once()


@pytest.mark.unit
def test_pull_provider_model_rejects_unsupported_provider(provider_test_client, provider_db_session):
    provider_db_session.execute.return_value.scalar_one_or_none.return_value.provider_name = "openai"
    provider = SimpleNamespace(
        supports_model_pulling=False,
        pull_model=AsyncMock(),
        delete_model=AsyncMock(),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.post(
            "/api/ai-providers/openai/models/pull",
            json={"name": "gpt-4o-mini", "insecure": False},
        )

    assert response.status_code == 400
    assert "does not support model pulling or deletion" in response.json()["detail"]
    provider.pull_model.assert_not_awaited()


@pytest.mark.unit
def test_delete_provider_model_calls_supported_provider(provider_test_client):
    provider = SimpleNamespace(
        supports_model_pulling=True,
        pull_model=AsyncMock(),
        delete_model=AsyncMock(),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.delete("/api/ai-providers/ollama/models/qwen2.5:7b-instruct")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    provider.delete_model.assert_awaited_once_with("qwen2.5:7b-instruct")


@pytest.mark.unit
def test_delete_provider_model_rejects_unsupported_provider(provider_test_client, provider_db_session):
    provider_db_session.execute.return_value.scalar_one_or_none.return_value.provider_name = "openai"
    provider = SimpleNamespace(
        supports_model_pulling=False,
        pull_model=AsyncMock(),
        delete_model=AsyncMock(),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.delete("/api/ai-providers/openai/models/gpt-4o-mini")

    assert response.status_code == 400
    assert "does not support model pulling or deletion" in response.json()["detail"]
    provider.delete_model.assert_not_awaited()


@pytest.mark.unit
def test_provider_generation_test_uses_configured_default_model(provider_test_client):
    provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=AIGenerateResponse(
                text="Provider is working.",
                model="qwen2.5:7b-instruct",
                provider="ollama",
            )
        ),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.post(
            "/api/ai-providers/ollama/test",
            json={"prompt": "Say OK"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "ollama",
        "model": "qwen2.5:7b-instruct",
        "success": True,
        "response_text": "Provider is working.",
        "error": None,
    }
    provider.generate.assert_awaited_once_with(
        model="qwen2.5:7b-instruct",
        prompt="Say OK",
        system=None,
        temperature=0.2,
        max_tokens=128,
    )


@pytest.mark.unit
def test_provider_generation_test_uses_requested_model(provider_test_client):
    provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=AIGenerateResponse(
                text="OK",
                model="custom-model",
                provider="ollama",
            )
        ),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.post(
            "/api/ai-providers/ollama/test",
            json={"prompt": "Say OK", "model": "custom-model", "system": "Be brief"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["model"] == "custom-model"
    provider.generate.assert_awaited_once_with(
        model="custom-model",
        prompt="Say OK",
        system="Be brief",
        temperature=0.2,
        max_tokens=128,
    )


@pytest.mark.unit
def test_provider_generation_test_requires_usable_model(provider_test_client, provider_db_session):
    provider_db_session.execute.return_value.scalar_one_or_none.return_value.default_model = None

    with patch("app.api.routers.ai_providers.provider_manager.get_provider") as mock_get_provider:
        response = provider_test_client.post(
            "/api/ai-providers/ollama/test",
            json={"prompt": "Say OK"},
        )

    assert response.status_code == 400
    assert "no default model" in response.json()["detail"]
    mock_get_provider.assert_not_called()


@pytest.mark.unit
def test_provider_generation_test_returns_structured_error(provider_test_client):
    provider = SimpleNamespace(generate=AsyncMock(side_effect=RuntimeError("connection refused")))

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.post(
            "/api/ai-providers/ollama/test",
            json={"prompt": "Say OK"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "ollama",
        "model": "qwen2.5:7b-instruct",
        "success": False,
        "response_text": None,
        "error": "connection refused",
    }


@pytest.mark.unit
def test_provider_generation_test_supplies_deeplx_language_kwargs(provider_test_client, provider_db_session):
    config_record = provider_db_session.execute.return_value.scalar_one_or_none.return_value
    config_record.provider_name = "deeplx"
    config_record.default_model = None
    provider = SimpleNamespace(
        generate=AsyncMock(
            return_value=AIGenerateResponse(
                text="Bonjour",
                model="translate",
                provider="deeplx",
            )
        ),
    )

    with patch(
        "app.api.routers.ai_providers.provider_manager.get_provider",
        return_value=provider,
    ):
        response = provider_test_client.post(
            "/api/ai-providers/deeplx/test",
            json={"prompt": "Hello", "target_lang": "FR"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    provider.generate.assert_awaited_once_with(
        model="translate",
        prompt="Hello",
        system=None,
        temperature=0.2,
        max_tokens=128,
        target_lang="FR",
    )


@pytest.mark.unit
def test_create_provider_config_clears_provider_cache(provider_test_client, provider_db_session):
    provider_db_session.execute.return_value.scalar_one_or_none.return_value = None

    def add_provider_config(provider_config):
        now = datetime.now(UTC)
        provider_config.id = uuid4()
        provider_config.is_enabled = False
        provider_config.timeout = 300
        provider_config.default_model = None
        provider_config.last_health_check = None
        provider_config.is_healthy = False
        provider_config.health_error = None
        provider_config.priority = 0
        provider_config.description = None
        provider_config.created_at = now
        provider_config.updated_at = now

    provider_db_session.add.side_effect = add_provider_config

    with patch("app.api.routers.ai_providers.provider_manager.clear_cache") as mock_clear_cache:
        response = provider_test_client.post(
            "/api/ai-providers",
            json={
                "provider_name": "ollama",
                "display_name": "Ollama",
                "base_url": "http://localhost:11434",
            },
        )

    assert response.status_code == 200
    mock_clear_cache.assert_called_once()


@pytest.mark.unit
def test_update_provider_config_clears_provider_cache(provider_test_client):
    with patch("app.api.routers.ai_providers.provider_manager.clear_cache") as mock_clear_cache:
        response = provider_test_client.post(
            "/api/ai-providers",
            json={
                "provider_name": "ollama",
                "display_name": "Ollama",
                "base_url": "http://localhost:11435",
            },
        )

    assert response.status_code == 200
    mock_clear_cache.assert_called_once()


@pytest.mark.unit
def test_update_provider_config_preserves_existing_api_key_when_blank(provider_test_client, provider_db_session):
    existing = provider_db_session.execute.return_value.scalar_one_or_none.return_value
    existing.api_key = "existing-secret"

    response = provider_test_client.post(
        "/api/ai-providers",
        json={
            "provider_name": "ollama",
            "display_name": "Ollama",
            "api_key": "   ",
            "base_url": "http://localhost:11435",
        },
    )

    assert response.status_code == 200
    assert existing.api_key == "existing-secret"
    assert response.json()["has_api_key"] is True


@pytest.mark.unit
def test_delete_provider_config_clears_provider_cache(provider_test_client):
    with patch("app.api.routers.ai_providers.provider_manager.clear_cache") as mock_clear_cache:
        response = provider_test_client.delete("/api/ai-providers/ollama")

    assert response.status_code == 200
    mock_clear_cache.assert_called_once()
