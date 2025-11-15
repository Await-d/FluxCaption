"""
Pydantic schemas for settings API endpoints.
"""

from typing import Literal
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Response schema for GET /api/settings endpoint."""

    # Jellyfin Integration
    jellyfin_base_url: str = Field(description="Jellyfin server base URL")
    jellyfin_api_key: str = Field(description="Jellyfin API key for authentication")
    jellyfin_timeout: int = Field(description="Jellyfin request timeout in seconds")
    jellyfin_max_retries: int = Field(description="Jellyfin maximum retry attempts")
    jellyfin_rate_limit_per_second: int = Field(description="Jellyfin API rate limit per second")

    # Ollama Configuration
    ollama_base_url: str = Field(description="Ollama API base URL")
    ollama_timeout: int = Field(description="Ollama request timeout in seconds")
    ollama_keep_alive: str = Field(description="Ollama model keep alive duration")

    # Subtitle & Translation Pipeline
    writeback_mode: Literal["upload", "sidecar"] = Field(description="Subtitle writeback mode")
    default_subtitle_format: Literal["srt", "ass", "vtt"] = Field(description="Default subtitle format")
    preserve_ass_styles: bool = Field(description="Preserve ASS styles when translating")
    translation_batch_size: int = Field(description="Number of lines to translate per batch")
    translation_max_line_length: int = Field(description="Maximum line length for subtitles")
    translation_preserve_formatting: bool = Field(description="Preserve formatting tags in translation")

    # Model Configuration
    default_mt_model: str = Field(description="Default machine translation model")
    asr_engine: Literal["faster-whisper", "funasr"] = Field(
        description="ASR engine to use (faster-whisper or funasr)"
    )
    asr_model: str = Field(description="Whisper ASR model (tiny/base/small/medium/large)")
    funasr_model: str = Field(description="FunASR model (paraformer-zh, sensevoicesmall, etc.)")
    asr_language: str = Field(description="Source language for ASR (auto for detection)")
    asr_compute_type: Literal["int8", "int8_float16", "float16", "float32"] = Field(
        description="ASR compute precision"
    )
    asr_device: Literal["cpu", "cuda", "auto"] = Field(description="ASR device")
    asr_beam_size: int = Field(description="Beam size for ASR decoding")
    asr_vad_filter: bool = Field(description="Enable voice activity detection")

    # Resource Limits
    max_concurrent_scan_tasks: int = Field(description="Max concurrent scan tasks")
    max_concurrent_translate_tasks: int = Field(description="Max concurrent translation tasks")
    max_concurrent_asr_tasks: int = Field(description="Max concurrent ASR tasks")
    max_upload_size_mb: int = Field(description="Maximum upload file size in MB")
    max_audio_duration_seconds: int = Field(description="Maximum audio duration in seconds")

    # Feature Flags
    enable_auto_scan: bool = Field(description="Enable automatic Jellyfin library scanning")
    enable_auto_pull_models: bool = Field(description="Automatically pull missing Ollama models")
    enable_sidecar_writeback: bool = Field(description="Enable sidecar file writeback")
    enable_metrics: bool = Field(description="Enable metrics collection")

    # Task Timeouts
    scan_task_timeout: int = Field(description="Scan task timeout in seconds")
    translate_task_timeout: int = Field(description="Translation task timeout in seconds")
    asr_task_timeout: int = Field(description="ASR task timeout in seconds")

    # Local Media Configuration
    favorite_media_paths: list[str] = Field(
        default_factory=list,
        description="List of favorite local media directory paths"
    )

    # System Info (read-only)
    environment: Literal["development", "production", "testing"] = Field(description="Current environment")
    db_vendor: Literal["postgres", "mysql", "sqlite", "mssql"] = Field(description="Database vendor")
    storage_backend: Literal["local", "s3"] = Field(description="Storage backend")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(description="Log level")

    class Config:
        from_attributes = True


class SettingsUpdateRequest(BaseModel):
    """Request schema for PATCH /api/settings endpoint."""

    # All fields are optional for partial updates
    
    # Jellyfin Integration
    jellyfin_base_url: str | None = Field(default=None, description="Jellyfin server base URL")
    jellyfin_api_key: str | None = Field(default=None, description="Jellyfin API key")
    jellyfin_timeout: int | None = Field(default=None, ge=5, le=300, description="Jellyfin timeout")
    jellyfin_max_retries: int | None = Field(default=None, ge=0, le=10, description="Jellyfin max retries")
    jellyfin_rate_limit_per_second: int | None = Field(default=None, ge=1, le=100, description="Jellyfin rate limit")

    # Ollama Configuration
    ollama_base_url: str | None = Field(default=None, description="Ollama API base URL")
    ollama_timeout: int | None = Field(default=None, ge=10, le=600, description="Ollama timeout in seconds")
    ollama_keep_alive: str | None = Field(default=None, description="Ollama keep alive duration (e.g., '30m', '1h')")

    writeback_mode: list[str] | None = Field(default=None, description="Required subtitle languages")
    writeback_mode: Literal["upload", "sidecar"] | None = Field(default=None, description="Writeback mode")
    default_subtitle_format: Literal["srt", "ass", "vtt"] | None = Field(
        default=None, description="Default subtitle format"
    )
    preserve_ass_styles: bool | None = Field(default=None, description="Preserve ASS styles")
    translation_batch_size: int | None = Field(default=None, ge=1, le=100, description="Translation batch size")
    translation_max_line_length: int | None = Field(default=None, ge=20, le=200, description="Max line length")
    translation_preserve_formatting: bool | None = Field(default=None, description="Preserve formatting")

    # Model Configuration
    default_mt_model: str | None = Field(default=None, description="Default MT model")
    asr_engine: Literal["faster-whisper", "funasr"] | None = Field(default=None, description="ASR engine")
    asr_model: str | None = Field(default=None, description="Whisper ASR model")
    funasr_model: str | None = Field(default=None, description="FunASR model")
    asr_language: str | None = Field(default=None, description="ASR source language")
    asr_compute_type: Literal["int8", "int8_float16", "float16", "float32"] | None = Field(
        default=None, description="ASR compute precision"
    )
    asr_device: Literal["cpu", "cuda", "auto"] | None = Field(default=None, description="ASR device")
    asr_beam_size: int | None = Field(default=None, ge=1, le=10, description="ASR beam size")
    asr_vad_filter: bool | None = Field(default=None, description="Enable VAD filter")

    # Resource Limits
    max_concurrent_scan_tasks: int | None = Field(default=None, ge=1, le=10, description="Max scan tasks")
    max_concurrent_translate_tasks: int | None = Field(default=None, ge=1, le=20, description="Max translate tasks")
    max_concurrent_asr_tasks: int | None = Field(default=None, ge=1, le=10, description="Max ASR tasks")
    max_upload_size_mb: int | None = Field(default=None, ge=1, le=2000, description="Max upload size MB")
    max_audio_duration_seconds: int | None = Field(default=None, ge=60, le=14400, description="Max audio duration")

    # Feature Flags
    enable_auto_scan: bool | None = Field(default=None, description="Enable auto scan")
    enable_auto_pull_models: bool | None = Field(default=None, description="Enable auto pull models")
    enable_sidecar_writeback: bool | None = Field(default=None, description="Enable sidecar writeback")
    enable_metrics: bool | None = Field(default=None, description="Enable metrics")

    # Task Timeouts
    scan_task_timeout: int | None = Field(default=None, ge=60, le=3600, description="Scan timeout")
    translate_task_timeout: int | None = Field(default=None, ge=60, le=7200, description="Translate timeout")
    asr_task_timeout: int | None = Field(default=None, ge=300, le=14400, description="ASR timeout")

    # Local Media Configuration
    favorite_media_paths: list[str] | None = Field(default=None, description="Favorite local media paths")
