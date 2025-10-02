"""
Pydantic schemas for settings API endpoints.
"""

from typing import Literal
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Response schema for GET /api/settings endpoint."""

    # Subtitle & Translation Pipeline
    required_langs: list[str] = Field(description="Required subtitle languages (BCP-47 codes)")
    writeback_mode: Literal["upload", "sidecar"] = Field(description="Subtitle writeback mode")
    default_subtitle_format: Literal["srt", "ass", "vtt"] = Field(description="Default subtitle format")
    preserve_ass_styles: bool = Field(description="Preserve ASS styles when translating")
    translation_batch_size: int = Field(description="Number of lines to translate per batch")
    translation_max_line_length: int = Field(description="Maximum line length for subtitles")
    translation_preserve_formatting: bool = Field(description="Preserve formatting tags in translation")

    # Model Configuration
    default_mt_model: str = Field(description="Default machine translation model")
    asr_model: str = Field(description="Whisper ASR model (tiny/base/small/medium/large)")
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
    required_langs: list[str] | None = Field(default=None, description="Required subtitle languages")
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
    asr_model: str | None = Field(default=None, description="Whisper ASR model")
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
