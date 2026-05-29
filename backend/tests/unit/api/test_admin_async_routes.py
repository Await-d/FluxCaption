from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers.ai_models import router as ai_models_router
from app.api.routers.auth import get_current_user
from app.api.routers.models import router as models_router
from app.api.routers.subtitle_sync import router as subtitle_sync_router
from app.core.db import get_db


class QueryStub:
    def __init__(self, first_result=None):
        self.first_result = first_result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.first_result

    def update(self, values):
        return 1


@contextmanager
def make_client(router, db_session):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.unit
def test_pull_model_queues_celery_and_marks_registry_pulling():
    db_session = MagicMock()
    db_session.query.return_value = QueryStub(first_result=None)
    task_result = SimpleNamespace(id="pull-task-id")

    with patch("app.api.routers.models.pull_model_task.apply_async", return_value=task_result) as apply_async:
        with make_client(models_router, db_session) as client:
            response = client.post("/api/models/pull", json={"name": "qwen2.5:7b-instruct"})

    assert response.status_code == 202
    assert response.json() == {
        "message": "Started pulling model 'qwen2.5:7b-instruct'",
        "status": "pulling",
        "task_id": "pull-task-id",
        "model": "qwen2.5:7b-instruct",
    }
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()
    apply_async.assert_called_once_with(args=["qwen2.5:7b-instruct"], queue="models")


@pytest.mark.unit
def test_sync_models_returns_queued_contract():
    db_session = MagicMock()
    task_result = SimpleNamespace(id="sync-task-id")

    with patch("app.api.routers.models.sync_models_task.apply_async", return_value=task_result) as apply_async:
        with make_client(models_router, db_session) as client:
            response = client.post("/api/models/sync")

    assert response.status_code == 202
    assert response.json() == {
        "status": "queued",
        "task_id": "sync-task-id",
        "message": "Model sync queued",
    }
    apply_async.assert_called_once_with(queue="models")
    db_session.query.assert_not_called()


@pytest.mark.unit
def test_test_model_queues_celery_after_registry_validation():
    model = SimpleNamespace(name="qwen2.5:7b-instruct")
    db_session = MagicMock()
    db_session.query.return_value = QueryStub(first_result=model)
    task_result = SimpleNamespace(id="test-task-id")

    with patch("app.api.routers.models.test_model_task.apply_async", return_value=task_result) as apply_async:
        with make_client(models_router, db_session) as client:
            response = client.post("/api/models/qwen2.5:7b-instruct/test")

    assert response.status_code == 202
    assert response.json() == {
        "status": "queued",
        "task_id": "test-task-id",
        "model": "qwen2.5:7b-instruct",
        "message": "Model test queued for 'qwen2.5:7b-instruct'",
    }
    apply_async.assert_called_once_with(args=["qwen2.5:7b-instruct"], queue="models")


@pytest.mark.unit
def test_sync_catalog_returns_queued_contract():
    db_session = MagicMock()
    task_result = SimpleNamespace(id="catalog-task-id")

    with patch(
        "app.api.routers.ai_models.sync_ai_model_catalog_task.apply_async",
        return_value=task_result,
    ) as apply_async:
        with make_client(ai_models_router, db_session) as client:
            response = client.post("/api/ai-models/sync-catalog?provider=openai")

    assert response.status_code == 202
    assert response.json() == {
        "status": "queued",
        "task_id": "catalog-task-id",
        "message": "AI model catalog sync queued",
        "source": "models.dev",
        "provider": "openai",
    }
    apply_async.assert_called_once_with(kwargs={"provider_name": "openai"}, queue="models")


@pytest.mark.unit
def test_subtitle_sync_queues_even_when_background_false():
    db_session = MagicMock()
    db_session.get.return_value = SimpleNamespace(id="subtitle-id")
    task_result = SimpleNamespace(id="subtitle-task-id")

    with patch(
        "app.api.routers.subtitle_sync.sync_subtitle_task.apply_async",
        return_value=task_result,
    ) as apply_async:
        with make_client(subtitle_sync_router, db_session) as client:
            response = client.post(
                "/api/v1/subtitle-sync/sync?background=false",
                json={"subtitle_id": "00000000-0000-0000-0000-000000000001", "mode": "full"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "status": "queued",
        "task_id": "subtitle-task-id",
        "subtitle_id": "00000000-0000-0000-0000-000000000001",
    }
    apply_async.assert_called_once_with(
        args=["00000000-0000-0000-0000-000000000001"],
        kwargs={"mode": "full", "paired_subtitle_id": None},
        queue="translate",
    )


@pytest.mark.unit
def test_asset_subtitle_sync_queues_even_when_background_false():
    db_session = MagicMock()
    db_session.get.return_value = SimpleNamespace(id="asset-id")
    task_result = SimpleNamespace(id="asset-task-id")

    with patch(
        "app.api.routers.subtitle_sync.sync_asset_subtitles_task.apply_async",
        return_value=task_result,
    ) as apply_async:
        with make_client(subtitle_sync_router, db_session) as client:
            response = client.post(
                "/api/v1/subtitle-sync/sync/asset?background=false",
                json={"asset_id": "00000000-0000-0000-0000-000000000002", "mode": "full"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "status": "queued",
        "task_id": "asset-task-id",
        "asset_id": "00000000-0000-0000-0000-000000000002",
    }
    apply_async.assert_called_once_with(
        args=["00000000-0000-0000-0000-000000000002"],
        kwargs={"mode": "full", "auto_pair": True},
        queue="translate",
    )
