"""
Subtitle file registry model.

Tracks generated subtitle files with their origin, storage location, and upload status.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import GUID

if TYPE_CHECKING:
    from app.models.media_asset import MediaAsset
    from app.models.subtitle_sync_record import SubtitleSyncRecord


# =============================================================================
# Subtitle Model
# =============================================================================

class Subtitle(BaseModel):
    """
    Represents a subtitle file generated or managed by the system.

    Tracks origin (ASR, MT, manual, Jellyfin), storage location,
    and upload/writeback status for Jellyfin integration.
    """
    __tablename__ = "subtitles"

    # Foreign Key
    asset_id: Mapped[Optional[GUID]] = mapped_column(
        GUID,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to parent media asset (null for standalone uploads)"
    )

    # Language and Format
    lang: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="BCP-47 language code (e.g., 'zh-CN', 'ja')"
    )

    format: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Subtitle format: srt, ass, vtt"
    )

    # Storage
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="File system path to the subtitle file"
    )

    # Origin Tracking
    origin: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="Origin: asr (auto-generated), mt (translated), manual (user upload), jellyfin (from Jellyfin)"
    )

    source_lang: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Source language for MT subtitles"
    )

    # Writeback Status
    is_uploaded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this subtitle has been written back to Jellyfin"
    )

    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of writeback to Jellyfin"
    )

    writeback_mode: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="How it was written back: upload (API) or sidecar (file)"
    )

    # Quality Metrics (optional)
    word_count: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Total word count (for quality metrics)"
    )

    line_count: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Total line/event count"
    )

    # Relationships
    asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset",
        back_populates="subtitles"
    )

    sync_records: Mapped[list["SubtitleSyncRecord"]] = relationship(
        "SubtitleSyncRecord",
        foreign_keys="SubtitleSyncRecord.subtitle_id",
        back_populates="subtitle",
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index("ix_subtitles_asset_lang", "asset_id", "lang"),
        Index("ix_subtitles_origin", "origin"),
        Index("ix_subtitles_uploaded", "is_uploaded"),
        Index("ix_subtitles_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Subtitle(id={self.id}, asset_id={self.asset_id}, lang={self.lang}, "
            f"origin={self.origin}, uploaded={self.is_uploaded})>"
        )
