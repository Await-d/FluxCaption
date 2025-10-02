"""
Translation Cache Service

Manages translation memory to avoid redundant AI translation calls.
"""

from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.translation_cache import TranslationCache

logger = get_logger(__name__)


class TranslationCacheService:
    """
    Service for managing translation cache.
    
    Provides methods to:
    - Check if a translation exists in cache
    - Save new translations to cache
    - Update cache hit statistics
    """

    def __init__(self, db: Session):
        self.db = db

    def get_cached_translation(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        model: str,
    ) -> Optional[str]:
        """
        Get cached translation if it exists.
        
        Args:
            source_text: Source text to translate
            source_lang: Source language code (BCP-47)
            target_lang: Target language code (BCP-47)
            model: Translation model name
            
        Returns:
            Cached translated text if found, None otherwise
        """
        # Compute hash for lookup
        content_hash = TranslationCache.compute_hash(
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
        )

        # Query cache
        stmt = select(TranslationCache).where(
            TranslationCache.content_hash == content_hash
        )
        cache_entry = self.db.execute(stmt).scalar_one_or_none()

        if cache_entry:
            # Update hit statistics
            cache_entry.hit_count += 1
            cache_entry.last_used_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.info(
                f"Cache HIT for {source_lang}->{target_lang} "
                f"(model={model}, hits={cache_entry.hit_count})"
            )
            return cache_entry.translated_text
        else:
            logger.info(
                f"Cache MISS for {source_lang}->{target_lang} (model={model})"
            )
            return None

    def save_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        model: str,
    ) -> None:
        """
        Save a new translation to cache.
        
        Args:
            source_text: Source text that was translated
            translated_text: Result of translation
            source_lang: Source language code (BCP-47)
            target_lang: Target language code (BCP-47)
            model: Translation model name used
        """
        # Compute hash
        content_hash = TranslationCache.compute_hash(
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
        )

        # Check if already exists (race condition protection)
        stmt = select(TranslationCache).where(
            TranslationCache.content_hash == content_hash
        )
        existing = self.db.execute(stmt).scalar_one_or_none()

        if existing:
            logger.debug(
                f"Translation already cached: {source_lang}->{target_lang} "
                f"(model={model})"
            )
            return

        # Create new cache entry
        cache_entry = TranslationCache(
            content_hash=content_hash,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            model=model,
            hit_count=0,
            created_at=datetime.now(timezone.utc),
            last_used_at=datetime.now(timezone.utc),
        )

        self.db.add(cache_entry)
        self.db.commit()

        logger.info(
            f"Saved translation to cache: {source_lang}->{target_lang} "
            f"(model={model}, text_len={len(source_text)})"
        )

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics:
                - total_entries: Total number of cached translations
                - total_hits: Sum of all hit counts
                - unique_language_pairs: Number of unique source->target pairs
                - unique_models: Number of unique models
        """
        from sqlalchemy import func

        # Total entries
        total_entries = self.db.query(func.count(TranslationCache.content_hash)).scalar()

        # Total hits
        total_hits = self.db.query(func.sum(TranslationCache.hit_count)).scalar() or 0

        # Unique language pairs
        unique_pairs = (
            self.db.query(
                func.count(
                    func.distinct(
                        TranslationCache.source_lang + "->" + TranslationCache.target_lang
                    )
                )
            ).scalar()
        )

        # Unique models
        unique_models = (
            self.db.query(func.count(func.distinct(TranslationCache.model))).scalar()
        )

        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "unique_language_pairs": unique_pairs,
            "unique_models": unique_models,
            "hit_rate": (
                round(total_hits / total_entries * 100, 2) if total_entries > 0 else 0
            ),
        }

    def get_entries(
        self,
        limit: int = 50,
        offset: int = 0,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        model: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "last_used_at",
        sort_order: str = "desc",
    ) -> dict:
        """
        Get paginated cache entries with filtering and sorting.

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            source_lang: Filter by source language
            target_lang: Filter by target language
            model: Filter by model name
            search: Search text in source_text or translated_text
            sort_by: Field to sort by (hit_count, created_at, last_used_at)
            sort_order: Sort order (asc, desc)

        Returns:
            Dictionary with entries and pagination info
        """
        from sqlalchemy import or_

        # Build query
        query = self.db.query(TranslationCache)

        # Apply filters
        if source_lang:
            query = query.filter(TranslationCache.source_lang == source_lang)
        if target_lang:
            query = query.filter(TranslationCache.target_lang == target_lang)
        if model:
            query = query.filter(TranslationCache.model == model)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TranslationCache.source_text.ilike(search_pattern),
                    TranslationCache.translated_text.ilike(search_pattern),
                )
            )

        # Get total count
        total = query.count()

        # Apply sorting
        sort_field = getattr(TranslationCache, sort_by, TranslationCache.last_used_at)
        if sort_order == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())

        # Apply pagination
        entries = query.limit(limit).offset(offset).all()

        # Convert to dict
        entries_data = [
            {
                "content_hash": entry.content_hash,
                "source_text": entry.source_text,
                "translated_text": entry.translated_text,
                "source_lang": entry.source_lang,
                "target_lang": entry.target_lang,
                "model": entry.model,
                "hit_count": entry.hit_count,
                "created_at": entry.created_at.isoformat(),
                "last_used_at": entry.last_used_at.isoformat(),
            }
            for entry in entries
        ]

        return {
            "entries": entries_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(entries_data) < total,
        }

    def clear_old_entries(self, days: int = 90) -> int:
        """
        Clear cache entries older than specified days with zero hits.

        Args:
            days: Number of days to keep entries

        Returns:
            Number of entries deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Delete entries with 0 hits older than cutoff date
        stmt = (
            self.db.query(TranslationCache)
            .filter(
                TranslationCache.hit_count == 0,
                TranslationCache.created_at < cutoff_date,
            )
        )

        count = stmt.count()
        stmt.delete(synchronize_session=False)
        self.db.commit()

        logger.info(f"Cleared {count} unused cache entries older than {days} days")
        return count

    def clear_all_entries(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        count = self.db.query(TranslationCache).count()
        self.db.query(TranslationCache).delete(synchronize_session=False)
        self.db.commit()

        logger.warning(f"Cleared ALL {count} cache entries")
        return count
