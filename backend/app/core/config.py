"""
Application configuration using pydantic-settings.

Loads and validates environment variables from .env file or system environment.
"""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =============================================================================
    # API & Application
    # =============================================================================
    api_base_url: str = Field(default="http://0.0.0.0:8000")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    environment: Literal["development", "production", "testing"] = Field(default="development")

    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # =============================================================================
    # Database Configuration
    # =============================================================================
    database_url: str = Field(
        ...,  # Required field
        description="Database connection URL"
    )
    db_vendor: Literal["postgres", "mysql", "sqlite", "mssql"] = Field(default="postgres")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=10)
    db_pool_pre_ping: bool = Field(default=True)

    # =============================================================================
    # Redis Configuration
    # =============================================================================
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=50)

    # =============================================================================
    # Celery Configuration
    # =============================================================================
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")
    celery_task_track_started: bool = Field(default=True)
    celery_task_time_limit: int = Field(default=3600)
    celery_worker_max_tasks_per_child: int = Field(default=100)
    celery_worker_prefetch_multiplier: int = Field(default=4)

    # =============================================================================
    # Jellyfin Integration
    # =============================================================================
    jellyfin_base_url: str = Field(
        ...,  # Required field
        description="Jellyfin server base URL"
    )
    jellyfin_api_key: str = Field(
        ...,  # Required field
        description="Jellyfin API key for authentication"
    )
    jellyfin_timeout: int = Field(default=30)
    jellyfin_max_retries: int = Field(default=3)
    jellyfin_rate_limit_per_second: int = Field(default=10)

    # =============================================================================
    # Ollama Configuration
    # =============================================================================
    ollama_base_url: str = Field(
        ...,  # Required field
        description="Ollama API base URL"
    )
    ollama_keep_alive: str = Field(default="30m")
    ollama_timeout: int = Field(default=300)
    default_mt_model: str = Field(default="qwen2.5:7b-instruct")
    ollama_pull_timeout: int = Field(default=3600)
    ollama_pull_retry_delay: int = Field(default=5)

    # =============================================================================
    # ASR Configuration
    # =============================================================================
    asr_model: str = Field(default="medium", description="Whisper model: tiny/base/small/medium/large")
    asr_compute_type: Literal["int8", "int8_float16", "float16", "float32"] = Field(default="int8")
    asr_device: Literal["cpu", "cuda", "auto"] = Field(default="auto")
    asr_beam_size: int = Field(default=5, description="Beam size for ASR decoding")
    asr_best_of: int = Field(default=5, description="Number of candidates when sampling")
    asr_vad_filter: bool = Field(default=True, description="Enable voice activity detection")
    asr_vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="VAD threshold")
    asr_language: str = Field(default="auto", description="Source language for ASR (auto for detection)")
    asr_model_cache_dir: str = Field(default="/app/models/whisper", description="Directory for Whisper models")
    asr_num_workers: int = Field(default=4, description="Number of CPU threads for ASR")
    asr_segment_duration: int = Field(default=600, description="Audio segment duration in seconds")
    asr_segment_overlap: int = Field(default=10, description="Overlap between segments in seconds")

    # =============================================================================
    # Subtitle & Translation Pipeline
    # =============================================================================
    required_langs: str = Field(default="zh-CN,en,ja")
    writeback_mode: Literal["upload", "sidecar"] = Field(default="upload")
    default_subtitle_format: Literal["srt", "ass", "vtt"] = Field(default="srt")
    preserve_ass_styles: bool = Field(default=True)
    translation_batch_size: int = Field(default=10)
    translation_max_line_length: int = Field(default=42)
    translation_preserve_formatting: bool = Field(default=True)

    @field_validator("required_langs")
    @classmethod
    def parse_required_langs(cls, v: str) -> list[str]:
        """Parse comma-separated required languages into a list."""
        return [lang.strip() for lang in v.split(",") if lang.strip()]

    # =============================================================================
    # File Storage
    # =============================================================================
    storage_backend: Literal["local", "s3"] = Field(default="local")
    temp_dir: str = Field(default="/tmp/fluxcaption")
    subtitle_output_dir: str = Field(default="/app/output/subtitles")

    # S3 Configuration (optional)
    s3_bucket: str | None = Field(default=None)
    s3_region: str | None = Field(default=None)
    s3_access_key: str | None = Field(default=None)
    s3_secret_key: str | None = Field(default=None)

    # =============================================================================
    # Logging Configuration
    # =============================================================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(default="json")
    log_output: Literal["stdout", "file", "both"] = Field(default="stdout")
    log_file: str = Field(default="/app/logs/fluxcaption.log")

    # =============================================================================
    # Security (Optional)
    # =============================================================================
    api_key_enabled: bool = Field(default=False)
    api_key: str | None = Field(default=None)
    jwt_secret_key: str | None = Field(default=None)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)

    # =============================================================================
    # Performance & Resource Limits
    # =============================================================================
    max_concurrent_scan_tasks: int = Field(default=2)
    max_concurrent_translate_tasks: int = Field(default=5)
    max_concurrent_asr_tasks: int = Field(default=2)

    scan_task_timeout: int = Field(default=300)
    translate_task_timeout: int = Field(default=1800)
    asr_task_timeout: int = Field(default=3600)

    max_upload_size_mb: int = Field(default=500)
    max_audio_duration_seconds: int = Field(default=7200)

    # =============================================================================
    # Feature Flags
    # =============================================================================
    enable_auto_scan: bool = Field(default=True)
    enable_auto_pull_models: bool = Field(default=True)
    enable_sidecar_writeback: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    enable_swagger_ui: bool = Field(default=True)

    # =============================================================================
    # Monitoring & Observability (Optional)
    # =============================================================================
    prometheus_enabled: bool = Field(default=False)
    prometheus_port: int = Field(default=9090)
    sentry_dsn: str | None = Field(default=None)
    sentry_environment: str | None = Field(default=None)

    # =============================================================================
    # Development Settings
    # =============================================================================
    debug: bool = Field(default=False)
    auto_reload: bool = Field(default=True)
    test_database_url: str | None = Field(default=None)


# =============================================================================
# Singleton Settings Instance
# =============================================================================
settings = Settings()


# =============================================================================
# Helper Functions
# =============================================================================

def get_settings() -> Settings:
    """
    Get the global settings instance.

    This function can be used as a FastAPI dependency.

    Returns:
        Settings: The global settings instance
    """
    return settings


def is_production() -> bool:
    """Check if the application is running in production mode."""
    return settings.environment == "production"


def is_development() -> bool:
    """Check if the application is running in development mode."""
    return settings.environment == "development"


def is_testing() -> bool:
    """Check if the application is running in testing mode."""
    return settings.environment == "testing"
