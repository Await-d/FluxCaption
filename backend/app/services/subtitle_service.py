"""
Subtitle processing service.

Handles loading, saving, and translating subtitle files (.srt, .ass, .vtt).
Preserves timing information and ASS formatting tags.
"""

import json
import re
from pathlib import Path

import pysubs2
import sqlalchemy as sa
from pysubs2 import SSAEvent, SSAFile

from app.core.config import settings
from app.core.logging import get_logger
from app.services.prompts import (
    SUBTITLE_TRANSLATION_SYSTEM_PROMPT,
    TRANSLATION_PROOFREADING_SYSTEM_PROMPT,
    build_proofreading_prompt,
    build_translation_prompt,
)
from app.services.translation_cache_service import TranslationCacheService
from app.services.unified_ai_client import UnifiedAIClient

logger = get_logger(__name__)


# =============================================================================
# AI Response Parsing
# =============================================================================


def extract_translation_from_response(response: str) -> str:
    """
    Extract translation from AI response, supporting JSON format and plain text.

    This function implements multiple fallback strategies to handle various AI output formats:
    1. Direct JSON parsing: {"translation": "text"}
    2. Markdown code block removal + JSON parsing
    3. Regex extraction of JSON object
    4. Common prefix removal (Translation:, etc.)
    5. Return original text as fallback

    Args:
        response: Raw response from AI model

    Returns:
        str: Extracted translation text
    """
    if not response:
        return ""

    response = response.strip()

    # Strategy 1: Try parsing entire response as JSON
    try:
        data = json.loads(response)
        if isinstance(data, dict) and "translation" in data:
            logger.debug("Extracted translation via direct JSON parsing")
            return data["translation"].strip()
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Remove markdown code blocks and try parsing
    # Handles cases like: ```json\n{"translation": "..."}\n```
    cleaned = re.sub(r"^```(?:json)?\s*\n?|\n?```$", "", response, flags=re.MULTILINE | re.DOTALL)
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "translation" in data:
            logger.debug("Extracted translation via markdown-cleaned JSON parsing")
            return data["translation"].strip()
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 3: Extract first JSON object with "translation" field using regex
    # Handles cases where JSON is embedded in text
    match = re.search(
        r'\{[^{}]*"translation"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*[^{}]*\}', response, re.DOTALL
    )
    if match:
        try:
            json_str = match.group(0)
            data = json.loads(json_str)
            if isinstance(data, dict) and "translation" in data:
                logger.debug("Extracted translation via regex JSON extraction")
                return data["translation"].strip()
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: Remove common prefixes that LLMs might add
    common_prefixes = [
        "Translation:",
        "Here's the translation:",
        "The translation is:",
        "Translated text:",
        "译文：",
        "翻译：",
        "翻译结果：",
    ]

    for prefix in common_prefixes:
        if response.lower().startswith(prefix.lower()):
            result = response[len(prefix) :].strip()
            logger.debug(f"Extracted translation by removing prefix: {prefix}")
            return result

    # Strategy 5: Return original response as fallback
    logger.debug("Using original response as translation (no extraction pattern matched)")
    return response


# =============================================================================
# ASS Tag Processing
# =============================================================================

# Regex pattern for ASS formatting tags
ASS_TAG_PATTERN = re.compile(r"\{[^}]+\}")


def strip_ass_tags(text: str) -> tuple[str, list[str]]:
    r"""
    Extract ASS formatting tags from text.

    Args:
        text: Text with ASS tags (e.g., "{\i1}Hello{\i0}")

    Returns:
        tuple: (plain_text, list_of_tags)
    """
    tags = ASS_TAG_PATTERN.findall(text)
    plain_text = ASS_TAG_PATTERN.sub("", text).strip()
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
    return "".join(tags) + translated_text


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
    text = " ".join(text.split())

    # Language-specific normalization
    if target_lang.startswith("zh"):
        # Chinese: use full-width punctuation
        replacements = {
            ",": "，",
            ".": "。",
            "!": "！",
            "?": "？",
            ":": "：",
            ";": "；",
        }
        for eng, chn in replacements.items():
            text = text.replace(eng, chn)

    elif target_lang.startswith("ja"):
        # Japanese: use Japanese punctuation
        replacements = {
            ",": "、",
            ".": "。",
            "!": "！",
            "?": "？",
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
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += word_length

    if current_line:
        lines.append(" ".join(current_line))

    return "\\N".join(lines)  # ASS line break


def apply_correction_rules(
    text: str, source_lang: str | None, target_lang: str | None, db_session: object | None = None
) -> str:
    """
    Apply correction rules to translated text.

    Args:
        text: Text to apply corrections to
        source_lang: Source language code
        target_lang: Target language code
        db_session: Database session

    Returns:
        str: Corrected text
    """
    if not db_session:
        return text

    try:
        from app.models.correction_rule import CorrectionRule

        # Get applicable rules
        stmt = sa.select(CorrectionRule).where(CorrectionRule.is_active)

        # Filter by language
        if source_lang:
            stmt = stmt.where(
                sa.or_(
                    CorrectionRule.source_lang == source_lang, CorrectionRule.source_lang.is_(None)
                )
            )
        if target_lang:
            stmt = stmt.where(
                sa.or_(
                    CorrectionRule.target_lang == target_lang, CorrectionRule.target_lang.is_(None)
                )
            )

        # Order by priority (higher priority first)
        stmt = stmt.order_by(CorrectionRule.priority.desc(), CorrectionRule.created_at.asc())

        rules = list(db_session.scalars(stmt).all())

        # Apply rules
        corrected_text = text
        applied_count = 0

        for rule in rules:
            try:
                if rule.is_regex:
                    # Use regex replacement
                    flags = 0 if rule.is_case_sensitive else re.IGNORECASE
                    pattern = re.compile(rule.source_pattern, flags)
                    new_text = pattern.sub(rule.target_text, corrected_text)
                else:
                    # Use simple string replacement
                    if rule.is_case_sensitive:
                        new_text = corrected_text.replace(rule.source_pattern, rule.target_text)
                    else:
                        # Case-insensitive replacement
                        pattern = re.compile(re.escape(rule.source_pattern), re.IGNORECASE)
                        new_text = pattern.sub(rule.target_text, corrected_text)

                # Track if rule was applied
                if new_text != corrected_text:
                    corrected_text = new_text
                    applied_count += 1

            except Exception as e:
                logger.warning(f"Failed to apply correction rule {rule.id}: {e}")
                continue

        if applied_count > 0:
            logger.debug(f"Applied {applied_count} correction rules to text")

        return corrected_text

    except Exception as e:
        logger.warning(f"Failed to apply correction rules: {e}")
        return text


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
    def save_subtitle(subs: SSAFile, file_path: str, format: str | None = None) -> None:
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
                format = suffix[1:] if suffix else "srt"

            # Validate format
            if format not in ["srt", "ass", "vtt"]:
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
        model: str | None = None,
        provider: str | None = None,
        batch_size: int = 10,
        preserve_formatting: bool = True,
        enable_proofreading: bool = True,
        progress_callback: callable | None = None,
        db_session: object | None = None,
        subtitle_id: str | None = None,
        asset_id: str | None = None,
        media_name: str | None = None,
    ) -> dict:
        """
        Translate a subtitle file using multi-provider AI support.

        Args:
            input_path: Input subtitle file path
            output_path: Output subtitle file path
            source_lang: Source language code
            target_lang: Target language code
            model: Model name to use (optional, uses default if not specified)
            provider: AI provider to use (optional, auto-selects if not specified)
            batch_size: Number of lines to translate per batch
            preserve_formatting: Whether to preserve ASS formatting
            enable_proofreading: Whether to enable AI proofreading of translations (default: True)
            progress_callback: Optional callback(completed, total) for progress
            db_session: Optional database session for caching and translation memory
            subtitle_id: Optional subtitle ID for translation memory linkage
            asset_id: Optional asset ID for translation memory linkage
            media_name: Optional media name for translation memory context

        Returns:
            dict: Translation statistics

        Raises:
            Exception: If translation fails
        """
        try:
            # Initialize unified AI client
            ai_client = UnifiedAIClient(db_session)

            # Resolve model and provider
            if not model:
                model = settings.default_mt_model

            logger.info(
                f"Starting subtitle translation: {source_lang} → {target_lang}\n"
                f"Model: {model}, Provider: {provider or 'auto'}"
            )

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
            proofread_count = 0

            # Initialize cache service if db session provided
            cache_service = TranslationCacheService(db_session) if db_session else None

            for i in range(0, total_events, batch_size):
                batch = texts_to_translate[i : i + batch_size]
                batch_end = min(i + batch_size, total_events)
                batch_num = i // batch_size + 1
                total_batches = (total_events + batch_size - 1) // batch_size

                logger.info(
                    f"\n{'=' * 80}\n"
                    f"开始翻译批次 {batch_num}/{total_batches} (行 {i + 1}-{batch_end}/{total_events})\n"
                    f"{source_lang} → {target_lang} | 模型: {model}\n"
                    f"{'=' * 80}"
                )

                # Process each line in the batch
                batch_translations = []
                for line_idx, line in enumerate(batch):
                    current_line_num = i + line_idx

                    # Get timing information from the subtitle event
                    event = subs[current_line_num]
                    start_time = event.start / 1000.0  # Convert ms to seconds
                    end_time = event.end / 1000.0

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
                        logger.info(
                            f"[行 {current_line_num + 1}/{total_events}] [缓存命中] "
                            f"原文: {line}\n"
                            f"译文: {cached_translation}"
                        )
                    else:
                        # No cache, do AI translation
                        prompt = build_translation_prompt(source_lang, target_lang, line)
                        translated = await ai_client.generate(
                            model=model,
                            prompt=prompt,
                            system=SUBTITLE_TRANSLATION_SYSTEM_PROMPT,
                            temperature=0.3,
                            provider=provider,
                        )
                        # Extract translation from AI response (supports JSON and plain text)
                        translated = extract_translation_from_response(translated)

                        # Log detailed translation
                        logger.info(
                            f"[行 {current_line_num + 1}/{total_events}] [AI翻译] "
                            f"{source_lang} → {target_lang}\n"
                            f"原文: {line}\n"
                            f"译文: {translated}"
                        )

                        # AI Proofreading: Review and improve the translation
                        if enable_proofreading and translated and line:
                            try:
                                proofread_prompt = build_proofreading_prompt(
                                    source_lang=source_lang,
                                    target_lang=target_lang,
                                    source_text=line,
                                    translated_text=translated,
                                )
                                proofread_result = await ai_client.generate(
                                    model=model,
                                    prompt=proofread_prompt,
                                    system=TRANSLATION_PROOFREADING_SYSTEM_PROMPT,
                                    temperature=0.2,  # Lower temperature for proofreading
                                    provider=provider,
                                )
                                # Extract translation from proofreading response (supports JSON and plain text)
                                proofread_result = extract_translation_from_response(
                                    proofread_result
                                )

                                # Only use proofread result if it's not empty
                                if proofread_result:
                                    # Log if proofreading made changes
                                    if proofread_result != translated:
                                        logger.info(
                                            f"[行 {current_line_num + 1}/{total_events}] [AI校对] 改进翻译\n"
                                            f"原文: {line}\n"
                                            f"初译: {translated}\n"
                                            f"校对: {proofread_result}"
                                        )
                                        proofread_count += 1
                                    else:
                                        logger.debug(
                                            f"[行 {current_line_num + 1}/{total_events}] [AI校对] 无需改进"
                                        )
                                    translated = proofread_result
                            except Exception as e:
                                logger.warning(
                                    f"Proofreading failed for line {current_line_num + 1}: {e}"
                                )
                                # Keep original translation if proofreading fails

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

                    # Save to translation memory
                    if db_session and line.strip():
                        try:
                            from app.models.translation_memory import TranslationMemory

                            tm_record = TranslationMemory(
                                subtitle_id=subtitle_id,
                                asset_id=asset_id,
                                source_text=line,
                                target_text=batch_translations[-1],
                                source_lang=source_lang,
                                target_lang=target_lang,
                                context=media_name,
                                line_number=current_line_num + 1,  # 1-indexed for display
                                start_time=start_time,
                                end_time=end_time,
                                word_count_source=len(line.split()),
                                word_count_target=len(batch_translations[-1].split()),
                                translation_model=model,
                            )
                            db_session.add(tm_record)
                            db_session.flush()  # Flush but don't commit yet
                        except Exception as e:
                            logger.warning(f"Failed to save translation memory record: {e}")

                    # Update progress after each line (real-time progress)
                    completed += 1
                    if progress_callback:
                        source_text = line[:50] + "..." if len(line) > 50 else line
                        target_text = (
                            batch_translations[-1][:50] + "..."
                            if len(batch_translations[-1]) > 50
                            else batch_translations[-1]
                        )
                        message = f"行 {current_line_num + 1}/{total_events}: {source_text} → {target_text}"
                        progress_callback(completed, total_events, message)

                translated_texts.extend(batch_translations)

                # Log batch completion
                logger.info(
                    f"\n{'-' * 80}\n"
                    f"批次 {batch_num}/{total_batches} 完成 ✓\n"
                    f"已翻译: {completed}/{total_events} 行 ({completed / total_events * 100:.1f}%)\n"
                    f"{'-' * 80}\n"
                )

            # Commit all translation memory records at once
            if db_session:
                try:
                    db_session.commit()
                    logger.info(f"Saved {len(translated_texts)} translation memory records")
                except Exception as e:
                    logger.warning(f"Failed to commit translation memory records: {e}")
                    db_session.rollback()

            # Log final translation statistics
            logger.info(
                f"\n{'=' * 80}\n"
                f"翻译完成汇总 - {source_lang} → {target_lang}\n"
                f"{'=' * 80}\n"
                f"总行数: {total_events}\n"
                f"已翻译: {len(translated_texts)}\n"
                f"跳过: {total_events - len(translated_texts)}\n"
                f"---\n"
                f"缓存命中: {cache_hits} ({(cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0:.1f}%)\n"
                f"AI翻译: {cache_misses}\n"
                f"AI校对改进: {proofread_count} ({(proofread_count / cache_misses * 100) if cache_misses > 0 else 0:.1f}%)\n"
                f"---\n"
                f"输出文件: {output_path}\n"
                f"{'=' * 80}\n"
            )

            # Apply translations back to subtitle events
            for idx, event in enumerate(subs):
                if idx < len(translated_texts):
                    translated_text = translated_texts[idx]

                    # Normalize text
                    translated_text = normalize_text(translated_text, target_lang)

                    # Apply correction rules
                    translated_text = apply_correction_rules(
                        translated_text,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        db_session=db_session,
                    )

                    # Split long lines if needed
                    if settings.translation_max_line_length > 0:
                        translated_text = split_long_line(
                            translated_text, settings.translation_max_line_length
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
                "proofread_improved": proofread_count,
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
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
            ".srt": "srt",
            ".ass": "ass",
            ".ssa": "ass",
            ".vtt": "vtt",
        }
        return format_map.get(suffix, "unknown")

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
        if format == "unknown":
            return False

        try:
            subs = SubtitleService.load_subtitle(file_path)
            return len(subs) > 0
        except Exception:
            return False

    @staticmethod
    def merge_srt_segments(
        segment_files: list[dict],
        output_path: str,
    ) -> dict:
        """
        Merge multiple SRT segment files into a single subtitle file.

        Each segment should have been generated from a specific time range
        of the source audio. This function adjusts timestamps to create
        continuous subtitles.

        Args:
            segment_files: List of segment info dicts with:
                - path: Path to SRT file
                - start: Start time of this segment in seconds
                - duration: Duration of this segment in seconds
            output_path: Path to save merged subtitle file

        Returns:
            dict: Merge statistics

        Raises:
            Exception: If merge fails
        """
        logger.info(f"Merging {len(segment_files)} SRT segments into {output_path}")

        merged_subs = pysubs2.SSAFile()
        total_events = 0

        for segment_idx, segment_info in enumerate(segment_files, start=1):
            segment_path = segment_info["path"]
            segment_start_ms = int(segment_info["start"] * 1000)  # Convert to milliseconds

            logger.debug(f"Processing segment {segment_idx}/{len(segment_files)}: {segment_path}")

            # Load segment subtitle
            if not Path(segment_path).exists():
                logger.warning(f"Segment file not found: {segment_path}, skipping")
                continue

            try:
                segment_subs = pysubs2.load(segment_path)
            except Exception as e:
                logger.error(f"Failed to load segment {segment_path}: {e}")
                continue

            # Adjust timestamps and merge events
            for event in segment_subs:
                # Create a copy of the event
                new_event = event.copy()

                # Adjust timestamps by adding segment start offset
                new_event.start += segment_start_ms
                new_event.end += segment_start_ms

                merged_subs.append(new_event)
                total_events += 1

        # Sort events by start time (important for proper subtitle display)
        merged_subs.sort()

        # Remove potential duplicates at segment boundaries
        # (due to overlap in audio segments)
        deduplicated_subs = pysubs2.SSAFile()
        last_event = None
        duplicates_removed = 0

        for event in merged_subs:
            # Check if this event is a duplicate of the last one
            if last_event and SubtitleService._are_events_duplicate(last_event, event):
                duplicates_removed += 1
                logger.debug(f"Removing duplicate event: {event.text[:50]}")
                continue

            deduplicated_subs.append(event)
            last_event = event

        # Save merged subtitle
        deduplicated_subs.save(output_path)

        logger.info(
            f"Merged {len(segment_files)} segments into {len(deduplicated_subs)} events "
            f"(removed {duplicates_removed} duplicates)"
        )

        return {
            "total_segments": len(segment_files),
            "total_events": len(deduplicated_subs),
            "duplicates_removed": duplicates_removed,
        }

    @staticmethod
    def _are_events_duplicate(
        event1: SSAEvent, event2: SSAEvent, time_threshold_ms: int = 100
    ) -> bool:
        """
        Check if two subtitle events are duplicates.

        Events are considered duplicates if they have:
        - Similar start time (within threshold)
        - Identical or very similar text

        Args:
            event1: First event
            event2: Second event
            time_threshold_ms: Maximum time difference to consider as duplicate (ms)

        Returns:
            bool: True if events are duplicates
        """
        # Check time proximity
        time_diff = abs(event1.start - event2.start)
        if time_diff > time_threshold_ms:
            return False

        # Check text similarity (normalize for comparison)
        text1 = event1.plaintext.strip().lower()
        text2 = event2.plaintext.strip().lower()

        # Exact match
        if text1 == text2:
            return True

        # Very similar (accounting for minor differences)
        # Calculate simple similarity ratio
        if len(text1) > 0 and len(text2) > 0:
            # Use Levenshtein-like comparison
            max_len = max(len(text1), len(text2))
            # Count matching characters
            matches = sum(c1 == c2 for c1, c2 in zip(text1, text2, strict=False))
            similarity = matches / max_len

            return similarity > 0.9  # 90% similarity threshold

        return False
