"""
Translation Job model.

Tracks translation tasks with status, progress, and error information.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TranslationJob(BaseModel):
    """
    Translation job tracking.

    Tracks all translation tasks including status, progress, and results.
    """

    __tablename__ = "translation_job"

    # Jellyfin Item ID (optional, for library scans)
    item_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Source type: subtitle | audio | media
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)

    # Source path (for manual uploads or local files)
    source_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Source language (BCP-47 code or 'auto')
    source_lang: Mapped[str] = mapped_column(String(20), nullable=False)

    # Target languages (JSON array: ["zh-CN", "en", "ja"])
    target_langs: Mapped[str] = mapped_column(Text, nullable=False)

    # Model used for translation
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    # AI Provider (ollama, openai, deepseek, claude, etc.)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Job status: queued | running | success | failed | canceled | paused
    # paused: 任务已暂停（通常因配额限额），等待配��重置后自动恢复
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)

    # Progress percentage (0-100)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Pause reason (if status is 'paused')
    # 例如: "daily_quota_exceeded", "monthly_quota_exceeded", "manual_pause"
    pause_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # When the job was paused
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # When to resume the job (usually next day for quota pause)
    resume_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Current phase: pull | asr | mt | post | writeback
    current_phase: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # Error message (if status is 'failed')
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Error stack trace
    error_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Job started timestamp
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Job finished timestamp
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Celery task ID
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Result file paths (JSON array)
    result_paths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Writeback mode: upload | sidecar
    writeback_mode: Mapped[str] = mapped_column(String(16), default="upload", nullable=False)

    # Retry count
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Max retries allowed
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    # Priority (higher = more important)
    priority: Mapped[int] = mapped_column(default=5, nullable=False)

    # Created by user/system
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Job metadata (JSON)
    job_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance metrics (JSON: {asr_time, mt_time, total_time})
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === Checkpoint/Resume Support ===
    # Intermediate results for resuming interrupted tasks

    # ASR output path (for asr_then_translate tasks)
    asr_output_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Completed phases (JSON array: ["pull", "extract", "asr"])
    completed_phases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Translated target languages (JSON array: ["zh-CN", "en"])
    # Tracks which languages have been successfully translated
    completed_target_langs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Last checkpoint timestamp
    last_checkpoint_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_job_status_created", "status", "created_at"),
        Index("idx_job_item_id", "item_id"),
        Index("idx_job_celery_task", "celery_task_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TranslationJob(id={self.id}, status={self.status}, "
            f"source_lang={self.source_lang}, target_langs={self.target_langs})>"
        )
