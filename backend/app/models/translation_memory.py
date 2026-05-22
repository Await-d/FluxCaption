"""
Translation Memory model.

Stores individual sentence-level translation pairs for building a translation memory database.
Each record represents one source sentence and its translation.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import GUID

if TYPE_CHECKING:
    from app.models.subtitle import Subtitle
    from app.models.media_asset import MediaAsset


# =============================================================================
# TranslationMemory Model
# =============================================================================

class TranslationMemory(BaseModel):
    """
    Represents a single translation pair (source → target).

    Used to build a translation memory database where users can search
    and review individual sentence translations.
    """
    __tablename__ = "translation_memory"

    # Foreign Keys
    subtitle_id: Mapped[Optional[GUID]] = mapped_column(
        GUID,
        ForeignKey("subtitles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to the subtitle file this translation came from"
    )

    asset_id: Mapped[Optional[GUID]] = mapped_column(
        GUID,
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to the media asset (for context)"
    )

    # Translation Pair
    source_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original source text (sentence/subtitle line)"
    )

    target_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Translated target text"
    )

    # Languages
    source_lang: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="BCP-47 source language code (e.g., 'en', 'ja')"
    )

    target_lang: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="BCP-47 target language code (e.g., 'zh-CN')"
    )

    # Context Information
    context: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Context information (e.g., media title, scene description)"
    )

    line_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Line/subtitle number in the original file"
    )

    # Timing Information (optional)
    start_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Start timestamp in seconds (for subtitle context)"
    )

    end_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="End timestamp in seconds (for subtitle context)"
    )

    # Quality/Metadata
    word_count_source: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Word count of source text"
    )

    word_count_target: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Word count of target text"
    )

    translation_model: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Name of the translation model used"
    )

    # Relationships
    subtitle: Mapped[Optional["Subtitle"]] = relationship(
        "Subtitle",
        foreign_keys=[subtitle_id]
    )

    asset: Mapped[Optional["MediaAsset"]] = relationship(
        "MediaAsset",
        foreign_keys=[asset_id]
    )

    __table_args__ = (
        # Index for searching by language pair
        Index("ix_tm_lang_pair", "source_lang", "target_lang"),
        # Index for searching source text
        Index("ix_tm_source_text", "source_text", postgresql_ops={"source_text": "gin_trgm_ops"}),
        # Index for searching target text
        Index("ix_tm_target_text", "target_text", postgresql_ops={"target_text": "gin_trgm_ops"}),
        # Index for filtering by subtitle
        Index("ix_tm_subtitle", "subtitle_id"),
        # Index for filtering by asset
        Index("ix_tm_asset", "asset_id"),
        # Index for time-based queries
        Index("ix_tm_created", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<TranslationMemory(id={self.id}, "
            f"{self.source_lang}→{self.target_lang}, "
            f"source='{self.source_text[:30]}...', "
            f"target='{self.target_text[:30]}...')>"
        )
