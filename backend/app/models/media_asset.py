"""
Media asset models for Jellyfin integration.

Tracks media items from Jellyfin library with their audio and subtitle language availability.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.types import GUID


# =============================================================================
# MediaAsset Model
# =============================================================================

class MediaAsset(BaseModel):
    """
    Represents a media item from Jellyfin.

    Tracks metadata about movies, episodes, or other media items
    to enable efficient querying for missing subtitle languages.
    """
    __tablename__ = "media_assets"

    # Jellyfin Identifiers
    item_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Jellyfin ItemId (unique identifier)"
    )

    library_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Jellyfin LibraryId (parent collection)"
    )

    # Media Metadata
    name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Display name of the media item"
    )

    path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="File system path to media file (for sidecar mode)"
    )

    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Media type: Movie, Episode, etc."
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Duration in milliseconds (from RunTimeTicks)"
    )

    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Content checksum for change detection"
    )

    # Relationships
    audio_langs: Mapped[list["MediaAudioLang"]] = relationship(
        "MediaAudioLang",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    subtitle_langs: Mapped[list["MediaSubtitleLang"]] = relationship(
        "MediaSubtitleLang",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    subtitles: Mapped[list["Subtitle"]] = relationship(
        "Subtitle",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index("ix_media_assets_library_created", "library_id", "created_at"),
        Index("ix_media_assets_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<MediaAsset(id={self.id}, item_id={self.item_id}, name={self.name})>"


# =============================================================================
# MediaAudioLang Model
# =============================================================================

class MediaAudioLang(BaseModel):
    """
    Tracks available audio languages for a media asset.

    Child table allows efficient querying like:
    "Find all items in library X with English audio"
    """
    __tablename__ = "media_audio_langs"

    # Foreign Key
    asset_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent media asset"
    )

    # Language Information
    lang: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="BCP-47 language code (e.g., 'en', 'zh-CN')"
    )

    codec: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Audio codec (aac, ac3, dts, etc.)"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default audio track"
    )

    # Relationship
    asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        back_populates="audio_langs"
    )

    __table_args__ = (
        Index("ix_media_audio_langs_asset_lang", "asset_id", "lang", unique=True),
        Index("ix_media_audio_langs_lang", "lang"),
    )

    def __repr__(self) -> str:
        return f"<MediaAudioLang(asset_id={self.asset_id}, lang={self.lang}, codec={self.codec})>"


# =============================================================================
# MediaSubtitleLang Model
# =============================================================================

class MediaSubtitleLang(BaseModel):
    """
    Tracks available subtitle languages for a media asset.

    Child table allows efficient querying like:
    "Find all items in library X missing zh-CN subtitles"
    """
    __tablename__ = "media_subtitle_langs"

    # Foreign Key
    asset_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent media asset"
    )

    # Language Information
    lang: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="BCP-47 language code (e.g., 'en', 'zh-CN')"
    )

    codec: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Subtitle codec (subrip, ass, webvtt, etc.)"
    )

    # Subtitle Properties
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default subtitle track"
    )

    is_forced: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a forced subtitle (for foreign language only)"
    )

    is_external: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this is a sidecar file (vs embedded in media)"
    )

    # Relationship
    asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        back_populates="subtitle_langs"
    )

    __table_args__ = (
        Index("ix_media_subtitle_langs_asset_lang", "asset_id", "lang"),
        Index("ix_media_subtitle_langs_lang", "lang"),
        Index("ix_media_subtitle_langs_external", "is_external"),
    )

    def __repr__(self) -> str:
        return (
            f"<MediaSubtitleLang(asset_id={self.asset_id}, lang={self.lang}, "
            f"external={self.is_external}, forced={self.is_forced})>"
        )
