"""
Translation Cache Model

Stores translation pairs to avoid redundant AI translation calls.
Uses content hash for efficient lookups.
"""

import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TranslationCache(Base):
    """
    Translation cache for storing previously translated text.
    
    This table acts as a translation memory, allowing the system to
    reuse translations for identical source texts, reducing AI API calls
    and improving translation consistency.
    """

    __tablename__ = "translation_cache"

    # Content hash (SHA256 of source_text + source_lang + target_lang + model)
    content_hash: Mapped[str] = mapped_column(
        String(64), primary_key=True, index=True,
        comment="SHA256 hash of source text, languages, and model"
    )
    
    # Source and target
    source_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Original text to translate"
    )
    translated_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Translated text result"
    )
    
    # Language pair
    source_lang: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Source language code (BCP-47)"
    )
    target_lang: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Target language code (BCP-47)"
    )
    
    # Model used
    model: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Translation model name"
    )
    
    # Usage tracking
    hit_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of times this cache entry was reused"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this translation was first cached"
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this cache entry was last accessed"
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_translation_cache_langs", "source_lang", "target_lang"),
        Index("ix_translation_cache_model", "model"),
        Index("ix_translation_cache_last_used", "last_used_at"),
    )

    @staticmethod
    def compute_hash(
        source_text: str,
        source_lang: str,
        target_lang: str,
        model: str,
    ) -> str:
        """
        Compute SHA256 hash for cache key.
        
        Args:
            source_text: Source text to translate
            source_lang: Source language code
            target_lang: Target language code
            model: Translation model name
            
        Returns:
            64-character hex string (SHA256 hash)
        """
        # Normalize inputs
        normalized = f"{source_text.strip()}|{source_lang}|{target_lang}|{model}"
        
        # Compute hash
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return (
            f"<TranslationCache("
            f"hash={self.content_hash[:8]}..., "
            f"{self.source_lang}->{self.target_lang}, "
            f"model={self.model}, "
            f"hits={self.hit_count}"
            f")>"
        )
