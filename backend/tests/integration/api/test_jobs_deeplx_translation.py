from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.routers.auth import get_current_user
from app.core import db as db_module
from app.core.config import settings
from app.core.db import get_db
from app.main import app
from app.models.ai_model_config import AIModelConfig
from app.models.ai_provider_config import AIProviderConfig
from app.models.ai_provider_usage import AIProviderQuota
from app.models.correction_rule import CorrectionRule
from app.models.task_log import TaskLog
from app.models.translation_job import TranslationJob
from app.models.translation_cache import TranslationCache
from app.models.translation_memory import TranslationMemory
from app.models.user import User
from app.services.ai_providers.base import AIGenerateResponse


@pytest.mark.integration
def test_translate_job_model_translate_routes_through_deeplx_provider(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    engine = sa.create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    TranslationJob.__table__.create(bind=engine)
    AIProviderConfig.__table__.create(bind=engine)
    AIModelConfig.__table__.create(bind=engine)
    AIProviderQuota.__table__.create(bind=engine)
    TranslationCache.__table__.create(bind=engine)
    TranslationMemory.__table__.create(bind=engine)
    CorrectionRule.__table__.create(bind=engine)

    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHello world.\n",
        encoding="utf-8",
    )

    with TestingSessionLocal() as session:
        session.add(
            AIProviderConfig(
                provider_name="deeplx",
                display_name="DeepLX",
                is_enabled=True,
                api_key=None,
                base_url="http://localhost:1188/translate",
                timeout=300,
                default_model="translate",
                is_healthy=True,
                priority=10,
                description="Integration test provider",
            )
        )
        session.add(
            AIModelConfig(
                provider_name="deeplx",
                model_name="translate",
                display_name="DeepLX Translate",
                is_enabled=True,
                model_type="translation",
                input_price=0.0,
                output_price=0.0,
                description="Integration test model",
                tags='["integration"]',
                is_default=True,
                priority=100,
                is_available=True,
            )
        )
        session.commit()

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    test_user = User(username="tester", email="tester@example.com", password_hash="unused")

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    @asynccontextmanager
    async def no_lifespan(_: object):
        yield

    original_session_local = db_module.SessionLocal
    original_output_dir = settings.subtitle_output_dir
    original_batch_size = settings.translation_batch_size
    original_proofreading = settings.enable_translation_proofreading
    original_lifespan = app.router.lifespan_context

    db_module.SessionLocal = TestingSessionLocal
    settings.subtitle_output_dir = str(output_dir)
    settings.translation_batch_size = 1
    settings.enable_translation_proofreading = False
    app.router.lifespan_context = no_lifespan

    try:
        with (
            patch("app.api.routers.jobs.dispatch_translation_job", return_value="test-celery-task-id"),
            patch("app.workers.tasks.event_publisher.publish_job_progress", AsyncMock()),
            patch("app.workers.tasks.save_task_log_sync", MagicMock()),
            patch("app.services.ai_quota_service.AIQuotaService.check_quota_with_pause", MagicMock()),
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/api/jobs/translate",
                    json={
                        "source_type": "subtitle",
                        "source_path": str(subtitle_path),
                        "source_lang": "en",
                        "target_langs": ["zh-CN"],
                        "model": "translate",
                        "writeback_mode": "sidecar",
                        "priority": 5,
                    },
                )

                assert response.status_code == 201, response.text
                payload = response.json()
                assert payload["model"] == "translate"
                assert payload["provider"] == "deeplx"
                assert payload["status"] == "queued"

                job_id = payload["id"]

                with TestingSessionLocal() as session:
                    job = session.query(TranslationJob).filter(TranslationJob.id == job_id).first()
                    assert job is not None
                    assert job.provider == "deeplx"
                    assert job.status == "queued"
                    assert job.current_phase is None
                    assert job.celery_task_id == "test-celery-task-id"

    finally:
        app.dependency_overrides.clear()
        db_module.SessionLocal = original_session_local
        settings.subtitle_output_dir = original_output_dir
        settings.translation_batch_size = original_batch_size
        settings.enable_translation_proofreading = original_proofreading
        app.router.lifespan_context = original_lifespan
        engine.dispose()


@pytest.mark.integration
def test_get_job_logs_returns_latest_page_in_chronological_order(tmp_path: Path):
    db_path = tmp_path / "logs.db"
    engine = sa.create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    TranslationJob.__table__.create(bind=engine)
    TaskLog.__table__.create(bind=engine)

    test_user = User(username="tester", email="tester@example.com", password_hash="unused")

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    async def override_get_current_user():
        return test_user

    @asynccontextmanager
    async def no_lifespan(_: object):
        yield

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = no_lifespan

    try:
        with TestingSessionLocal() as session:
            job = TranslationJob(
                source_type="subtitle",
                source_path=str(tmp_path / "source.srt"),
                source_lang="en",
                target_langs=json.dumps(["zh-CN"]),
                model="translate",
                provider="deeplx",
                status="completed",
            )
            session.add(job)
            session.commit()
            session.refresh(job)

            for index in range(1, 6):
                session.add(
                    TaskLog(
                        job_id=str(job.id),
                        phase="mt",
                        status=f"log-{index}",
                        progress=float(index * 10),
                    )
                )
            session.commit()

            job_id = str(job.id)

        with TestClient(app) as client:
            response = client.get(f"/api/jobs/{job_id}/logs", params={"limit": 2, "offset": 1})

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total_logs"] == 5
        assert payload["limit"] == 2
        assert payload["offset"] == 1
        assert payload["has_more"] is True
        assert [entry["status"] for entry in payload["logs"]] == ["log-3", "log-4"]

    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan
        engine.dispose()
