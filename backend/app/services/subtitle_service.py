"""
Subtitle processing service.

Handles loading, saving, and translating subtitle files (.srt, .ass, .vtt).
Preserves timing information and ASS formatting tags.
"""

import re
from pathlib import Path
from typing import Optional
import pysubs2
from pysubs2 import SSAFile, SSAEvent

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ollama_client import ollama_client
from app.services.prompts import (
    SUBTITLE_TRANSLATION_SYSTEM_PROMPT,
    BATCH_TRANSLATION_SYSTEM_PROMPT,
    build_translation_prompt,
    build_batch_translation_prompt,
)
from app.services.translation_cache_service import TranslationCacheService

logger = get_logger(__name__)


# =============================================================================
# ASS Tag Processing
# =============================================================================

# Regex pattern for ASS formatting tags
ASS_TAG_PATTERN = re.compile(r'\{[^}]+\}')


def strip_ass_tags(text: str) -> tuple[str, list[str]]:
    """
    Extract ASS formatting tags from text.

    Args:
        text: Text with ASS tags (e.g., "{\i1}Hello{\i0}")

    Returns:
        tuple: (plain_text, list_of_tags)
    """
    tags = ASS_TAG_PATTERN.findall(text)
    plain_text = ASS_TAG_PATTERN.sub('', text).strip()
    return plain_text, tags


def restore_tags(tags: list[str], translated_text: str) -> str:
    """
    Restore ASS tags to translated text.

    Simple strategy: place all tags at the beginning.

    Args:
        tags: List of ASS tags
        translated_text: Translated plain text

    Returns:
        str: Text with tags restored
    """
    if not tags:
        return translated_text

    # Place all tags at the beginning
    return ''.join(tags) + translated_text


# =============================================================================
# Text Normalization
# =============================================================================

def normalize_text(text: str, target_lang: str) -> str:
    """
    Normalize text for subtitle display.

    Args:
        text: Text to normalize
        target_lang: Target language code

    Returns:
        str: Normalized text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())

    # Language-specific normalization
    if target_lang.startswith('zh'):
        # Chinese: use full-width punctuation
        replacements = {
            ',': '，',
            '.': '。',
            '!': '！',
            '?': '？',
            ':': '：',
            ';': '；',
        }
        for eng, chn in replacements.items():
            text = text.replace(eng, chn)

    elif target_lang.startswith('ja'):
        # Japanese: use Japanese punctuation
        replacements = {
            ',': '、',
            '.': '。',
            '!': '！',
            '?': '？',
        }
        for eng, jpn in replacements.items():
            text = text.replace(eng, jpn)

    return text


def split_long_line(text: str, max_length: int = 42) -> str:
    """
    Split long subtitle lines into multiple lines.

    Args:
        text: Text to split
        max_length: Maximum characters per line

    Returns:
        str: Text with line breaks inserted
    """
    if len(text) <= max_length:
        return text

    # Try to split at punctuation or spaces
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word) + (1 if current_line else 0)  # +1 for space

        if current_length + word_length > max_length and current_line:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += word_length

    if current_line:
        lines.append(' '.join(current_line))

    return '\\N'.join(lines)  # ASS line break


# =============================================================================
# Subtitle File Operations
# =============================================================================

class SubtitleService:
    """Service for subtitle file operations."""

    @staticmethod
    def load_subtitle(file_path: str) -> SSAFile:
        """
        Load a subtitle file.

        Args:
            file_path: Path to subtitle file

        Returns:
            SSAFile: Loaded subtitle file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        try:
            subs = pysubs2.load(file_path)
            logger.info(f"Loaded subtitle file: {file_path} ({len(subs)} events)")
            return subs
        except FileNotFoundError:
            logger.error(f"Subtitle file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load subtitle file: {e}", exc_info=True)
            raise ValueError(f"Invalid subtitle file: {e}")

    @staticmethod
    def save_subtitle(subs: SSAFile, file_path: str, format: Optional[str] = None) -> None:
        """
        Save a subtitle file.

        Args:
            subs: Subtitle data to save
            file_path: Output file path
            format: Output format ('srt', 'ass', 'vtt'), auto-detected if None

        Raises:
            ValueError: If format is invalid
        """
        try:
            # Determine format from file extension if not specified
            if format is None:
                suffix = Path(file_path).suffix.lower()
                format = suffix[1:] if suffix else 'srt'

            # Validate format
            if format not in ['srt', 'ass', 'vtt']:
                raise ValueError(f"Unsupported subtitle format: {format}")

            # Ensure output directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Save with specified format
            subs.save(file_path, format=format)
            logger.info(f"Saved subtitle file: {file_path} (format={format})")

        except Exception as e:
            logger.error(f"Failed to save subtitle file: {e}", exc_info=True)
            raise

    @staticmethod
    async def translate_subtitle(
        input_path: str,
        output_path: str,
        source_lang: str,
        target_lang: str,
        model: str,
        batch_size: int = 10,
        preserve_formatting: bool = True,
        progress_callback: Optional[callable] = None,
        db_session: Optional[object] = None,
    ) -> dict:
        """
        Translate a subtitle file.

        Args:
            input_path: Input subtitle file path
            output_path: Output subtitle file path
            source_lang: Source language code
            target_lang: Target language code
            model: Ollama model to use
            batch_size: Number of lines to translate per batch
            preserve_formatting: Whether to preserve ASS formatting
            progress_callback: Optional callback(completed, total) for progress

        Returns:
            dict: Translation statistics

        Raises:
            Exception: If translation fails
        """
        try:
            # Load subtitle
            subs = SubtitleService.load_subtitle(input_path)
            total_events = len(subs)

            if total_events == 0:
                logger.warning("Subtitle file is empty")
                return {"translated": 0, "total": 0, "skipped": 0}

            # Extract texts for translation
            texts_to_translate = []
            tags_list = []

            for event in subs:
                if preserve_formatting:
                    plain_text, tags = strip_ass_tags(event.text)
                else:
                    plain_text, tags = event.text, []

                texts_to_translate.append(plain_text)
                tags_list.append(tags)

            # Translate in batches
            translated_texts = []
            completed = 0
            cache_hits = 0
            cache_misses = 0

            # Initialize cache service if db session provided
            cache_service = TranslationCacheService(db_session) if db_session else None

            for i in range(0, total_events, batch_size):
                batch = texts_to_translate[i:i + batch_size]
                batch_end = min(i + batch_size, total_events)

                logger.info(f"Translating batch {i // batch_size + 1}: lines {i}-{batch_end}")

                # Process each line in the batch
                batch_translations = []
                for line in batch:
                    # Check cache first if available
                    cached_translation = None
                    if cache_service and line.strip():
                        cached_translation = cache_service.get_cached_translation(
                            source_text=line,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            model=model,
                        )

                    if cached_translation:
                        # Use cached translation
                        batch_translations.append(cached_translation)
                        cache_hits += 1
                    else:
                        # No cache, do AI translation
                        prompt = build_translation_prompt(source_lang, target_lang, line)
                        translated = await ollama_client.generate(
                            model=model,
                            prompt=prompt,
                            system=SUBTITLE_TRANSLATION_SYSTEM_PROMPT,
                            temperature=0.3,
                        )
                        translated = translated.strip()
                        batch_translations.append(translated)
                        cache_misses += 1

                        # Save to cache for future use
                        if cache_service and line.strip():
                            try:
                                cache_service.save_translation(
                                    source_text=line,
                                    translated_text=translated,
                                    source_lang=source_lang,
                                    target_lang=target_lang,
                                    model=model,
                                )
                            except Exception as e:
                                logger.warning(f"Failed to save translation to cache: {e}")

                translated_texts.extend(batch_translations)
                completed += len(batch)

                # Progress callback
                if progress_callback:
                    progress_callback(completed, total_events)

            # Log cache statistics
            if cache_service:
                logger.info(
                    f"Translation cache stats: {cache_hits} hits, {cache_misses} misses, "
                    f"hit rate: {(cache_hits / (cache_hits + cache_misses) * 100):.1f}%"
                )

            # Apply translations back to subtitle events
            for idx, event in enumerate(subs):
                if idx < len(translated_texts):
                    translated_text = translated_texts[idx]

                    # Normalize text
                    translated_text = normalize_text(translated_text, target_lang)

                    # Split long lines if needed
                    if settings.translation_max_line_length > 0:
                        translated_text = split_long_line(
                            translated_text,
                            settings.translation_max_line_length
                        )

                    # Restore formatting tags
                    if preserve_formatting and idx < len(tags_list):
                        translated_text = restore_tags(tags_list[idx], translated_text)

                    event.text = translated_text

            # Save translated subtitle
            SubtitleService.save_subtitle(subs, output_path)

            return {
                "translated": len(translated_texts),
                "total": total_events,
                "skipped": total_events - len(translated_texts),
            }

        except Exception as e:
            logger.error(f"Subtitle translation failed: {e}", exc_info=True)
            raise

    @staticmethod
    def detect_format(file_path: str) -> str:
        """
        Detect subtitle file format from extension.

        Args:
            file_path: File path

        Returns:
            str: Format ('srt', 'ass', 'vtt', or 'unknown')
        """
        suffix = Path(file_path).suffix.lower()
        format_map = {
            '.srt': 'srt',
            '.ass': 'ass',
            '.ssa': 'ass',
            '.vtt': 'vtt',
        }
        return format_map.get(suffix, 'unknown')

    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        Validate that a file is a supported subtitle file.

        Args:
            file_path: File path to validate

        Returns:
            bool: True if valid, False otherwise
        """
        format = SubtitleService.detect_format(file_path)
        if format == 'unknown':
            return False

        try:
            subs = SubtitleService.load_subtitle(file_path)
            return len(subs) > 0
        except Exception:
            return False
