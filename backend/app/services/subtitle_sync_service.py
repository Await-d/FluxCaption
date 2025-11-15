"""
Subtitle Synchronization Service

Automatically sync subtitle files to translation memory for building a comprehensive
translation database.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from uuid import UUID

import pysubs2
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.subtitle import Subtitle
from app.models.subtitle_sync_record import SubtitleSyncRecord
from app.models.translation_memory import TranslationMemory
from app.models.media_asset import MediaAsset

logger = get_logger(__name__)


# =============================================================================
# Subtitle Matching Algorithm
# =============================================================================

class SubtitleMatcher:
    """
    Matches subtitle lines between source and target subtitles based on timestamps.
    """

    def __init__(self, time_tolerance_ms: int = 100):
        """
        Initialize matcher.

        Args:
            time_tolerance_ms: Maximum time difference to consider a match (milliseconds)
        """
        self.time_tolerance_ms = time_tolerance_ms

    def match_by_timestamp(
        self,
        source_events: List[pysubs2.SSAEvent],
        target_events: List[pysubs2.SSAEvent]
    ) -> List[Tuple[pysubs2.SSAEvent, pysubs2.SSAEvent, float]]:
        """
        Match subtitle events by timestamp.

        Args:
            source_events: Source subtitle events
            target_events: Target subtitle events

        Returns:
            List of (source_event, target_event, confidence) tuples
        """
        matches = []

        for source_event in source_events:
            best_match = None
            best_confidence = 0.0

            for target_event in target_events:
                confidence = self._calculate_timestamp_confidence(
                    source_event, target_event
                )

                if confidence > best_confidence:
                    best_match = target_event
                    best_confidence = confidence

            # Only include matches with confidence > 0.5
            if best_match and best_confidence > 0.5:
                matches.append((source_event, best_match, best_confidence))

        return matches

    def _calculate_timestamp_confidence(
        self,
        event1: pysubs2.SSAEvent,
        event2: pysubs2.SSAEvent
    ) -> float:
        """
        Calculate timestamp matching confidence.

        Args:
            event1: First event
            event2: Second event

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Calculate time differences
        start_diff = abs(event1.start - event2.start)
        end_diff = abs(event1.end - event2.end)

        # Perfect match
        if start_diff == 0 and end_diff == 0:
            return 1.0

        # Within tolerance
        if start_diff <= self.time_tolerance_ms and end_diff <= self.time_tolerance_ms:
            # Calculate confidence based on closeness
            start_score = 1.0 - (start_diff / self.time_tolerance_ms)
            end_score = 1.0 - (end_diff / self.time_tolerance_ms)
            return (start_score + end_score) / 2

        # Check if events overlap
        overlap = self._calculate_overlap(event1, event2)
        if overlap > 0:
            # Return confidence based on overlap percentage
            duration1 = event1.end - event1.start
            duration2 = event2.end - event2.start
            avg_duration = (duration1 + duration2) / 2
            return overlap / avg_duration if avg_duration > 0 else 0.0

        return 0.0

    def _calculate_overlap(
        self,
        event1: pysubs2.SSAEvent,
        event2: pysubs2.SSAEvent
    ) -> float:
        """
        Calculate overlap duration between two events.

        Args:
            event1: First event
            event2: Second event

        Returns:
            Overlap duration in milliseconds
        """
        start = max(event1.start, event2.start)
        end = min(event1.end, event2.end)
        return max(0, end - start)


# =============================================================================
# Subtitle Sync Service
# =============================================================================

class SubtitleSyncService:
    """
    Service for synchronizing subtitle files to translation memory.
    """

    def __init__(self, session: Session):
        """
        Initialize service.

        Args:
            session: Database session
        """
        self.session = session
        self.matcher = SubtitleMatcher()

    def sync_subtitle_to_memory(
        self,
        subtitle_id: str,
        mode: str = "incremental",
        paired_subtitle_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> SubtitleSyncRecord:
        """
        Sync a subtitle file to translation memory.

        Args:
            subtitle_id: Subtitle ID to sync
            mode: Sync mode ('full', 'incremental', 'skip')
            paired_subtitle_id: Optional paired subtitle ID for translation pairs
            progress_callback: Optional progress callback(completed, total, message)

        Returns:
            SubtitleSyncRecord: Sync record with results

        Raises:
            ValueError: If subtitle not found or file doesn't exist
        """
        # Load subtitle from database
        subtitle = self.session.get(Subtitle, UUID(subtitle_id))
        if not subtitle:
            raise ValueError(f"Subtitle {subtitle_id} not found")

        # Check if file exists
        if not Path(subtitle.storage_path).exists():
            raise ValueError(f"Subtitle file not found: {subtitle.storage_path}")

        # Create sync record
        sync_record = SubtitleSyncRecord(
            subtitle_id=subtitle.id,
            asset_id=subtitle.asset_id,
            status="running",
            sync_mode=mode,
            paired_subtitle_id=UUID(paired_subtitle_id) if paired_subtitle_id else None,
            started_at=datetime.now(timezone.utc)
        )
        self.session.add(sync_record)
        self.session.flush()

        try:
            # Load subtitle file
            subs = pysubs2.load(subtitle.storage_path)
            sync_record.total_lines = len(subs)

            # Load paired subtitle if provided
            paired_subs = None
            paired_subtitle = None
            if paired_subtitle_id:
                paired_subtitle = self.session.get(Subtitle, UUID(paired_subtitle_id))
                if paired_subtitle and Path(paired_subtitle.storage_path).exists():
                    paired_subs = pysubs2.load(paired_subtitle.storage_path)
                    logger.info(
                        f"Loaded paired subtitle: {paired_subtitle.lang} "
                        f"({len(paired_subs)} lines)"
                    )

            # Process based on mode
            if mode == "incremental":
                # Check last sync time
                last_sync = self._get_last_successful_sync(subtitle_id)
                if last_sync and subtitle.updated_at <= last_sync.created_at:
                    logger.info(f"Subtitle {subtitle_id} unchanged since last sync, skipping")
                    sync_record.status = "success"
                    sync_record.skipped_lines = sync_record.total_lines
                    sync_record.finished_at = datetime.now(timezone.utc)
                    self.session.commit()
                    return sync_record

            # Match subtitles if paired
            matches = []
            if paired_subs:
                logger.info(
                    f"Matching {len(subs)} source lines with {len(paired_subs)} target lines"
                )
                matches = self.matcher.match_by_timestamp(subs, paired_subs)
                logger.info(f"Found {len(matches)} matched pairs")

            # Sync to translation memory
            synced = 0
            skipped = 0
            failed = 0

            for idx, event in enumerate(subs, start=1):
                try:
                    # Extract text
                    source_text = event.plaintext.strip()
                    if not source_text:
                        skipped += 1
                        continue

                    # Get timing info
                    start_time = event.start / 1000.0  # Convert to seconds
                    end_time = event.end / 1000.0

                    # Get context
                    context = None
                    if subtitle.asset:
                        context = subtitle.asset.name

                    # Find target text if paired
                    target_text = None
                    target_lang = None
                    if paired_subs and matches:
                        # Find matching target event
                        for source_ev, target_ev, confidence in matches:
                            if source_ev == event:
                                target_text = target_ev.plaintext.strip()
                                target_lang = paired_subtitle.lang
                                break

                    # If we have a translation pair
                    if target_text and target_lang:
                        # Check if already exists (skip mode)
                        if mode == "skip":
                            exists = self._translation_exists(
                                source_text, subtitle.lang, target_text, target_lang
                            )
                            if exists:
                                skipped += 1
                                continue

                        # Create translation memory record
                        tm_record = TranslationMemory(
                            subtitle_id=subtitle.id,
                            asset_id=subtitle.asset_id,
                            source_text=source_text,
                            target_text=target_text,
                            source_lang=subtitle.lang,
                            target_lang=target_lang,
                            context=context,
                            line_number=idx,
                            start_time=start_time,
                            end_time=end_time,
                            word_count_source=len(source_text.split()),
                            word_count_target=len(target_text.split()),
                            translation_model="subtitle_sync"  # Mark as synced from subtitle
                        )
                        self.session.add(tm_record)
                        synced += 1
                    else:
                        # No paired subtitle, just save as source-only record
                        # This can be useful for future reference
                        # Skip for now to avoid cluttering the database
                        skipped += 1

                    # Report progress
                    if progress_callback and idx % 10 == 0:
                        progress_callback(idx, len(subs), f"Syncing line {idx}/{len(subs)}")

                except Exception as e:
                    logger.warning(f"Failed to sync line {idx}: {e}")
                    failed += 1
                    continue

            # Commit all records
            self.session.commit()

            # Update sync record
            sync_record.synced_lines = synced
            sync_record.skipped_lines = skipped
            sync_record.failed_lines = failed
            sync_record.status = "success"
            sync_record.finished_at = datetime.now(timezone.utc)
            self.session.commit()

            logger.info(
                f"Sync completed: {synced} synced, {skipped} skipped, {failed} failed"
            )

            return sync_record

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            sync_record.status = "failed"
            sync_record.error_message = str(e)
            sync_record.finished_at = datetime.now(timezone.utc)
            self.session.commit()
            raise

    def discover_subtitle_pairs(
        self,
        asset_id: str
    ) -> List[Tuple[Subtitle, Subtitle]]:
        """
        Discover all possible subtitle pairs for an asset.

        Args:
            asset_id: Media asset ID

        Returns:
            List of (source_subtitle, target_subtitle) tuples
        """
        # Get all subtitles for this asset
        subtitles = self.session.query(Subtitle).filter(
            Subtitle.asset_id == UUID(asset_id)
        ).all()

        logger.info(f"Found {len(subtitles)} subtitles for asset {asset_id}")

        # Create pairs (avoid duplicates)
        pairs = []
        for i, source_sub in enumerate(subtitles):
            for target_sub in subtitles[i+1:]:
                if source_sub.lang != target_sub.lang:
                    pairs.append((source_sub, target_sub))

        logger.info(f"Discovered {len(pairs)} subtitle pairs")
        return pairs

    def sync_asset_subtitles(
        self,
        asset_id: str,
        mode: str = "incremental",
        auto_pair: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Sync all subtitles for a media asset.

        Args:
            asset_id: Media asset ID
            mode: Sync mode
            auto_pair: Automatically pair subtitles for translation memory
            progress_callback: Progress callback

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting asset subtitle sync: {asset_id}")

        # Get asset
        asset = self.session.get(MediaAsset, UUID(asset_id))
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        results = {
            "asset_id": asset_id,
            "asset_name": asset.name,
            "total_subtitles": 0,
            "synced_subtitles": 0,
            "failed_subtitles": 0,
            "sync_records": []
        }

        # Discover subtitle pairs
        pairs = []
        if auto_pair:
            pairs = self.discover_subtitle_pairs(asset_id)
            logger.info(f"Auto-pairing enabled: found {len(pairs)} pairs")

        # Get all subtitles
        subtitles = self.session.query(Subtitle).filter(
            Subtitle.asset_id == UUID(asset_id)
        ).all()

        results["total_subtitles"] = len(subtitles)

        # Track which subtitles have been paired
        paired_subtitle_ids = set()
        for source_sub, target_sub in pairs:
            paired_subtitle_ids.add(str(source_sub.id))
            paired_subtitle_ids.add(str(target_sub.id))

        # Sync paired subtitles
        for idx, (source_sub, target_sub) in enumerate(pairs, start=1):
            try:
                logger.info(
                    f"Syncing pair {idx}/{len(pairs)}: "
                    f"{source_sub.lang} ↔ {target_sub.lang}"
                )

                # Sync source → target
                sync_record = self.sync_subtitle_to_memory(
                    subtitle_id=str(source_sub.id),
                    mode=mode,
                    paired_subtitle_id=str(target_sub.id),
                    progress_callback=progress_callback
                )
                results["sync_records"].append({
                    "subtitle_id": str(source_sub.id),
                    "lang": source_sub.lang,
                    "paired_lang": target_sub.lang,
                    "status": sync_record.status,
                    "synced_lines": sync_record.synced_lines
                })

                if sync_record.status == "success":
                    results["synced_subtitles"] += 1
                else:
                    results["failed_subtitles"] += 1

            except Exception as e:
                logger.error(f"Failed to sync pair: {e}")
                results["failed_subtitles"] += 1

        logger.info(
            f"Asset sync completed: {results['synced_subtitles']} synced, "
            f"{results['failed_subtitles']} failed"
        )

        return results

    def _get_last_successful_sync(
        self,
        subtitle_id: str
    ) -> Optional[SubtitleSyncRecord]:
        """
        Get the last successful sync record for a subtitle.

        Args:
            subtitle_id: Subtitle ID

        Returns:
            Last successful sync record or None
        """
        return self.session.query(SubtitleSyncRecord).filter(
            SubtitleSyncRecord.subtitle_id == UUID(subtitle_id),
            SubtitleSyncRecord.status == "success"
        ).order_by(SubtitleSyncRecord.created_at.desc()).first()

    def _translation_exists(
        self,
        source_text: str,
        source_lang: str,
        target_text: str,
        target_lang: str
    ) -> bool:
        """
        Check if a translation pair already exists.

        Args:
            source_text: Source text
            source_lang: Source language
            target_text: Target text
            target_lang: Target language

        Returns:
            True if exists, False otherwise
        """
        exists = self.session.query(TranslationMemory).filter(
            TranslationMemory.source_text == source_text,
            TranslationMemory.source_lang == source_lang,
            TranslationMemory.target_text == target_text,
            TranslationMemory.target_lang == target_lang
        ).first()

        return exists is not None

    def get_sync_status(
        self,
        subtitle_id: str
    ) -> Optional[SubtitleSyncRecord]:
        """
        Get the latest sync status for a subtitle.

        Args:
            subtitle_id: Subtitle ID

        Returns:
            Latest sync record or None
        """
        return self.session.query(SubtitleSyncRecord).filter(
            SubtitleSyncRecord.subtitle_id == UUID(subtitle_id)
        ).order_by(SubtitleSyncRecord.created_at.desc()).first()

