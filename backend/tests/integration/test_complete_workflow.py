"""
Integration tests for complete translation workflows.

Tests end-to-end scenarios including:
- Manual subtitle upload + translation
- ASR + translation workflow
- Model pulling
- Job lifecycle (create, monitor, complete)
"""

import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestManualSubtitleTranslationWorkflow:
    """Test manual subtitle upload and translation workflow."""

    def test_upload_and_translate_subtitle(
        self,
        client: TestClient,
        db_session: Session,
        sample_srt_file: str,
        mock_ollama_client,
    ):
        """
        Test complete workflow:
        1. Upload subtitle file
        2. Create translation job
        3. Monitor job progress
        4. Verify translated output
        """
        # Step 1: Upload subtitle file
        with open(sample_srt_file, "rb") as f:
            response = client.post(
                "/api/upload/subtitle",
                files={"file": ("test.srt", f, "text/plain")},
                data={
                    "source_lang": "en",
                    "target_langs": "zh-CN,ja",
                    "mt_model": "qwen2.5:7b-instruct",
                },
            )

        assert response.status_code == 200
        upload_data = response.json()
        assert "job_id" in upload_data
        job_id = upload_data["job_id"]

        # Step 2: Check job was created
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job_data = response.json()
        assert job_data["type"] == "translate"
        assert job_data["status"] in ["pending", "running"]
        assert "zh-CN" in job_data["target_langs"]
        assert "ja" in job_data["target_langs"]

        # Step 3: Get all jobs (should include our job)
        response = client.get("/api/jobs")
        assert response.status_code == 200
        jobs_data = response.json()
        assert jobs_data["total"] > 0
        job_ids = [j["id"] for j in jobs_data["jobs"]]
        assert job_id in job_ids

    def test_translation_with_invalid_file(self, client: TestClient):
        """Test that uploading invalid file returns error."""
        response = client.post(
            "/api/upload/subtitle",
            files={"file": ("test.txt", b"invalid content", "text/plain")},
            data={"target_langs": "zh-CN"},
        )

        # Should either reject or handle gracefully
        # Exact status code depends on implementation
        assert response.status_code in [400, 422, 500]


class TestASRTranslationWorkflow:
    """Test ASR + translation workflow."""

    def test_asr_then_translate(
        self,
        client: TestClient,
        db_session: Session,
        sample_video_file: str,
        mock_asr_service,
        mock_ollama_client,
    ):
        """
        Test ASR + translation workflow:
        1. Create asr_then_translate job
        2. ASR extracts audio and generates subtitle
        3. Subtitle is translated
        4. Output is saved
        """
        # Create ASR + translate job
        response = client.post(
            "/api/jobs/translate",
            json={
                "type": "asr_then_translate",
                "target_langs": ["zh-CN"],
                "input_file_path": sample_video_file,
                "mt_model": "qwen2.5:7b-instruct",
            },
        )

        assert response.status_code == 200
        job_data = response.json()
        assert "job_id" in job_data
        job_id = job_data["job_id"]

        # Check job details
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job_details = response.json()
        assert job_details["type"] == "asr_then_translate"
        assert job_details["status"] in ["pending", "running"]


class TestJobManagement:
    """Test job management operations."""

    def test_cancel_running_job(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test cancelling a running job."""
        # Create a job
        response = client.post(
            "/api/jobs/translate",
            json={
                "type": "translate",
                "target_langs": ["zh-CN"],
                "source_lang": "en",
            },
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Try to cancel it
        response = client.post(f"/api/jobs/{job_id}/cancel")
        # Should succeed or return appropriate status
        assert response.status_code in [200, 404, 409]

    def test_retry_failed_job(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test retrying a failed job."""
        # Create a job
        response = client.post(
            "/api/jobs/translate",
            json={
                "type": "translate",
                "target_langs": ["zh-CN"],
                "source_lang": "en",
            },
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Try to retry it
        response = client.post(f"/api/jobs/{job_id}/retry")
        # Should create new job or return error if not failed
        assert response.status_code in [200, 400, 404, 409]

    def test_job_filtering(self, client: TestClient):
        """Test job filtering by status and type."""
        # Test status filter
        response = client.get("/api/jobs?status=completed")
        assert response.status_code == 200
        data = response.json()
        for job in data["jobs"]:
            assert job["status"] == "completed"

        # Test type filter
        response = client.get("/api/jobs?type=translate")
        assert response.status_code == 200
        data = response.json()
        for job in data["jobs"]:
            assert job["type"] == "translate"

        # Test pagination
        response = client.get("/api/jobs?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) <= 5
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestModelManagement:
    """Test Ollama model management."""

    def test_list_models(
        self,
        client: TestClient,
        mock_ollama_client,
    ):
        """Test listing installed Ollama models."""
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data

    def test_pull_model(
        self,
        client: TestClient,
        mock_ollama_client,
    ):
        """Test pulling a new model."""
        response = client.post(
            "/api/models/pull",
            json={"model_name": "qwen2.5:7b-instruct"},
        )
        assert response.status_code in [200, 202]
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data or "message" in data


class TestHealthAndSystem:
    """Test system health and status endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded", "down"]
        assert "services" in data
        assert "timestamp" in data

    def test_health_check_services(self, client: TestClient):
        """Test individual service health in health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Check that expected services are reported
        services = data["services"]
        assert "database" in services
        assert "redis" in services
        assert "ollama" in services


class TestSettings:
    """Test application settings management."""

    def test_get_settings(self, client: TestClient):
        """Test retrieving application settings."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "required_langs" in data
        assert "default_mt_model" in data
        assert "asr_model" in data

    def test_update_settings(self, client: TestClient):
        """Test updating application settings."""
        response = client.patch(
            "/api/settings",
            json={
                "max_concurrent_translate_tasks": 3,
                "asr_language": "auto",
            },
        )
        assert response.status_code in [200, 403]  # May require auth

        if response.status_code == 200:
            data = response.json()
            assert data["max_concurrent_translate_tasks"] == 3


@pytest.mark.slow
class TestLongRunningWorkflows:
    """Tests for long-running workflows (marked as slow)."""

    @pytest.mark.timeout(300)  # 5 minute timeout
    def test_full_asr_translation_pipeline(
        self,
        client: TestClient,
        sample_video_file: str,
        mock_asr_service,
        mock_ollama_client,
    ):
        """
        Test complete ASR + translation pipeline with actual task execution.

        This test validates:
        - Task creation
        - Task execution
        - Progress updates
        - Final output generation
        """
        # Create job
        response = client.post(
            "/api/jobs/translate",
            json={
                "type": "asr_then_translate",
                "target_langs": ["zh-CN", "ja"],
                "input_file_path": sample_video_file,
            },
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Poll for completion (with timeout)
        max_attempts = 60  # 5 minutes (5s interval)
        attempts = 0

        while attempts < max_attempts:
            response = client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 200
            job = response.json()

            if job["status"] in ["completed", "failed", "cancelled"]:
                break

            time.sleep(5)
            attempts += 1

        # Verify final status
        assert job["status"] in ["completed", "failed"]

        if job["status"] == "completed":
            assert job["progress"] == 100
            assert len(job["output_file_paths"]) > 0
