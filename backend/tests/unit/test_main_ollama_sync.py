import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _load_main_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DB_VENDOR", "sqlite")
    monkeypatch.setenv("ENVIRONMENT", "testing")

    config_module = importlib.import_module("app.core.config")
    importlib.reload(config_module)

    db_module = importlib.import_module("app.core.db")
    importlib.reload(db_module)

    main_module = importlib.import_module("app.main")
    return importlib.reload(main_module)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_models_from_ollama_if_available_skips_when_unreachable(monkeypatch):
    main = _load_main_module(monkeypatch)
    db = MagicMock()

    with patch.object(
        main.ollama_client,
        "health_check",
        new=AsyncMock(return_value=False),
    ) as mock_health, patch(
        "app.core.model_sync.sync_models_from_ollama",
        new=AsyncMock(),
    ) as mock_sync:
        result = await main.sync_models_from_ollama_if_available(db)

    assert result is False
    mock_health.assert_awaited_once_with(log_errors=False)
    mock_sync.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_models_from_ollama_if_available_syncs_when_reachable(monkeypatch):
    main = _load_main_module(monkeypatch)
    db = MagicMock()

    with patch.object(
        main.ollama_client,
        "health_check",
        new=AsyncMock(return_value=True),
    ) as mock_health, patch(
        "app.core.model_sync.sync_models_from_ollama",
        new=AsyncMock(),
    ) as mock_sync:
        result = await main.sync_models_from_ollama_if_available(db)

    assert result is True
    mock_health.assert_awaited_once_with(log_errors=False)
    mock_sync.assert_awaited_once_with(db)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ai_model_catalog_sync_loop_exits_on_cancellation(monkeypatch):
    main = _load_main_module(monkeypatch)

    task = asyncio.create_task(main.ai_model_catalog_sync_loop())
    await asyncio.sleep(0)
    task.cancel()

    await task
    assert task.done()
    assert not task.cancelled()
