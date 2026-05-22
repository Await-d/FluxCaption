"""
Subtitle Sync Record Model

Tracks synchronization status of subtitle files to translation memory.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import GUID

if TYPE_CHECKING:
    from app.models.subtitle import Subtitle
    from app.models.media_asset import MediaAsset


# =============================================================================
# SubtitleSyncRecord Model
# =============================================================================

class SubtitleSyncRecord(BaseModel):
    """
    Tracks synchronization of subtitle files to translation memory.
    
    Used to avoid redundant syncing and support incremental updates.
    """
    __tablename__ = "subtitle_sync_records"

    # Foreign Keys
    subtitle_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("subtitles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the subtitle file that was synced"
    )

    asset_id: Mapped[Optional[GUID]] = mapped_column(
        GUID,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to the media asset"
    )

    # Sync Status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="Sync status: pending, running, success, failed"
    )

    sync_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Sync mode: full, incremental, skip"
    )

    # Statistics
    total_lines: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of subtitle lines"
    )

    synced_lines: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of lines successfully synced"
    )

    skipped_lines: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of lines skipped (already exists)"
    )

    failed_lines: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of lines that failed to sync"
    )

    # Paired Subtitle (if syncing as translation pair)
    paired_subtitle_id: Mapped[Optional[GUID]] = mapped_column(
        GUID,
        ForeignKey("subtitles.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to paired subtitle for translation memory"
    )

    # Timing Information
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When sync started"
    )

    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When sync finished"
    )

    # Error Information
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if sync failed"
    )

    # Relationships
    subtitle: Mapped["Subtitle"] = relationship(
        "Subtitle",
        foreign_keys=[subtitle_id],
        back_populates="sync_records"
    )

    paired_subtitle: Mapped[Optional["Subtitle"]] = relationship(
        "Subtitle",
        foreign_keys=[paired_subtitle_id]
    )

    asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset",
        foreign_keys=[asset_id]
    )

    __table_args__ = (
        Index("ix_subtitle_sync_subtitle", "subtitle_id"),
        Index("ix_subtitle_sync_asset", "asset_id"),
        Index("ix_subtitle_sync_status", "status"),
        Index("ix_subtitle_sync_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SubtitleSyncRecord(id={self.id}, subtitle_id={self.subtitle_id}, "
            f"status={self.status}, synced={self.synced_lines}/{self.total_lines})>"
        )

