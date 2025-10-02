"""
Pytest configuration for integration tests.

Provides fixtures for testing complete workflows with real services.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import Base, get_db
from app.core.config import settings


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    # Use test database URL if available, otherwise use configured URL
    test_db_url = settings.test_database_url or settings.database_url
    engine = create_engine(test_db_url, pool_pre_ping=True, future=True)

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        future=True
    )

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# FastAPI Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Service Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_ollama_client(monkeypatch):
    """Mock Ollama client for testing without actual LLM calls."""
    from unittest.mock import Mock, AsyncMock

    mock = Mock()
    mock.generate = AsyncMock(return_value={
        "response": "Translated text",
        "done": True,
    })
    mock.list_models = AsyncMock(return_value={
        "models": [
            {"name": "qwen2.5:7b-instruct", "size": 4000000000}
        ]
    })
    mock.pull_model = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def mock_jellyfin_client(monkeypatch):
    """Mock Jellyfin client for testing without actual Jellyfin server."""
    from unittest.mock import Mock, AsyncMock

    mock = Mock()
    mock.get_libraries = AsyncMock(return_value=[
        {
            "Id": "test-lib-1",
            "Name": "Test Movies",
            "CollectionType": "movies",
        }
    ])
    mock.get_items = AsyncMock(return_value=[
        {
            "Id": "test-item-1",
            "Name": "Test Movie",
            "Path": "/media/test.mp4",
            "MediaStreams": [
                {"Type": "Audio", "Language": "eng"},
                {"Type": "Subtitle", "Language": "eng"},
            ],
        }
    ])
    mock.upload_subtitle = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def mock_asr_service(monkeypatch):
    """Mock ASR service for testing without actual Whisper model."""
    from unittest.mock import Mock

    mock = Mock()
    mock.transcribe_to_srt = Mock(return_value={
        "output_path": "/tmp/test_output.srt",
        "language": "en",
        "duration": 120.5,
        "num_segments": 10,
    })

    return mock


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_srt_file(tmp_path):
    """Create a sample SRT subtitle file for testing."""
    srt_content = """1
00:00:00,000 --> 00:00:02,000
Hello, world!

2
00:00:02,000 --> 00:00:04,000
This is a test subtitle.

3
00:00:04,000 --> 00:00:06,000
Testing translation features.
"""

    srt_file = tmp_path / "test_subtitle.srt"
    srt_file.write_text(srt_content, encoding="utf-8")
    return str(srt_file)


@pytest.fixture
def sample_video_file(tmp_path):
    """Create a dummy video file for testing (just an empty file)."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"")  # Empty file for testing
    return str(video_file)


# =============================================================================
# Celery Task Fixtures
# =============================================================================

@pytest.fixture
def celery_worker():
    """Mock Celery worker for testing tasks."""
    # For integration tests, we might want to use eager mode
    from app.workers.celery_app import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    yield celery_app

    # Reset
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files(tmp_path):
    """Automatically cleanup temporary files after each test."""
    yield
    # Cleanup logic here if needed
    pass
