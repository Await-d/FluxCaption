"""
Script to update existing subtitle records with missing word_count and line_count.

Run this script to populate missing statistics for existing subtitles in the database.
"""

from app.core.db import SessionLocal
from app.models.subtitle import Subtitle
from app.core.logging import get_logger
import pysubs2
from pathlib import Path

logger = get_logger(__name__)


def update_subtitle_stats():
    """Update existing subtitle records with missing word_count and line_count."""

    session = SessionLocal()

    try:
        # Get all subtitles
        subtitles = session.query(Subtitle).all()

        logger.info(f"Found {len(subtitles)} subtitle records")

        updated_count = 0
        failed_count = 0

        for subtitle in subtitles:
            # Check if already has word_count
            if subtitle.word_count and subtitle.word_count > 0:
                continue

            try:
                # Load subtitle file
                if not Path(subtitle.storage_path).exists():
                    logger.warning(f"Subtitle file not found: {subtitle.storage_path}")
                    failed_count += 1
                    continue

                # Parse subtitle file
                subs = pysubs2.load(subtitle.storage_path)

                # Calculate stats
                line_count = len(subs)
                word_count = sum(len(event.text.split()) for event in subs)

                # Update record
                subtitle.line_count = line_count
                subtitle.word_count = word_count

                updated_count += 1

                if updated_count % 10 == 0:
                    logger.info(f"Updated {updated_count} subtitles so far...")

            except Exception as e:
                logger.error(f"Failed to update subtitle {subtitle.id}: {e}")
                failed_count += 1
                continue

        # Commit changes
        session.commit()

        logger.info(f"✅ Successfully updated {updated_count} subtitle records")
        if failed_count > 0:
            logger.warning(f"⚠️  Failed to update {failed_count} subtitle records")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update subtitle stats: {e}", exc_info=True)
        raise

    finally:
        session.close()


if __name__ == "__main__":
    update_subtitle_stats()
