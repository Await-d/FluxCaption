"""
Missing language detection service.

Analyzes Jellyfin media items to determine which subtitle languages are missing
based on configured requirements.
"""

from typing import Optional

from app.core.logging import get_logger
from app.schemas.jellyfin import JellyfinItem, MediaStream

logger = get_logger(__name__)


# =============================================================================
# Language Code Normalization
# =============================================================================

# ISO 639-2 (3-letter) to BCP-47 mapping for common languages
ISO639_2_TO_BCP47 = {
    "eng": "en",
    "chi": "zh-CN",  # Simplified Chinese (default)
    "zho": "zh-CN",
    "jpn": "ja",
    "kor": "ko",
    "fre": "fr",
    "fra": "fr",
    "ger": "de",
    "deu": "de",
    "spa": "es",
    "rus": "ru",
    "ita": "it",
    "por": "pt",
    "ara": "ar",
    "hin": "hi",
    "tha": "th",
    "vie": "vi",
}


def normalize_language_code(language: Optional[str], language_tag: Optional[str] = None) -> str:
    """
    Normalize language code to BCP-47 format.

    Jellyfin provides both 3-letter ISO 639-2 codes and BCP-47 tags.
    We prefer BCP-47 but fall back to converting ISO 639-2.

    Args:
        language: ISO 639-2 3-letter code (e.g., "eng", "chi")
        language_tag: BCP-47 tag (e.g., "en", "zh-CN")

    Returns:
        Normalized BCP-47 code, or "und" for undefined

    Examples:
        >>> normalize_language_code("eng", "en")
        "en"
        >>> normalize_language_code("chi", None)
        "zh-CN"
        >>> normalize_language_code(None, "ja")
        "ja"
        >>> normalize_language_code(None, None)
        "und"
    """
    # Prefer BCP-47 tag if available
    if language_tag:
        return language_tag.lower()

    # Fall back to ISO 639-2 conversion
    if language:
        language_lower = language.lower()
        return ISO639_2_TO_BCP47.get(language_lower, language_lower)

    # Undefined language
    return "und"


# =============================================================================
# Detector
# =============================================================================

class LanguageDetector:
    """
    Detects missing subtitle languages for Jellyfin media items.

    Analyzes MediaStreams from Jellyfin items and compares against
    required languages to determine what's missing.
    """

    @staticmethod
    def extract_subtitle_languages(item: JellyfinItem) -> list[str]:
        """
        Extract all subtitle language codes from a Jellyfin item.

        Args:
            item: Jellyfin item with MediaSources

        Returns:
            List of unique BCP-47 language codes for existing subtitles
        """
        languages = set()

        # Iterate through all media sources
        for source in item.media_sources:
            for stream in source.media_streams:
                # Only process subtitle streams
                if stream.type.lower() != "subtitle":
                    continue

                # Normalize language code
                lang = normalize_language_code(stream.language, stream.language_tag)

                # Skip undefined languages
                if lang != "und":
                    languages.add(lang)

        return sorted(list(languages))

    @staticmethod
    def extract_audio_languages(item: JellyfinItem) -> list[str]:
        """
        Extract all audio language codes from a Jellyfin item.

        Args:
            item: Jellyfin item with MediaSources

        Returns:
            List of unique BCP-47 language codes for existing audio
        """
        languages = set()

        # Iterate through all media sources
        for source in item.media_sources:
            for stream in source.media_streams:
                # Only process audio streams
                if stream.type.lower() != "audio":
                    continue

                # Normalize language code
                lang = normalize_language_code(stream.language, stream.language_tag)

                # Skip undefined languages
                if lang != "und":
                    languages.add(lang)

        return sorted(list(languages))

    @staticmethod
    def detect_missing_languages(
        item: JellyfinItem,
        required_langs: list[str],
        check_type: str = "subtitle",
    ) -> list[str]:
        """
        Detect which required languages are missing from an item.

        Args:
            item: Jellyfin item to analyze
            required_langs: List of required BCP-47 language codes
            check_type: Type to check - "subtitle" or "audio"

        Returns:
            List of missing language codes (sorted)

        Examples:
            >>> item = JellyfinItem(...)  # Has en, ja subtitles
            >>> detect_missing_languages(item, ["en", "zh-CN", "ja"])
            ["zh-CN"]
        """
        if check_type == "subtitle":
            existing_langs = LanguageDetector.extract_subtitle_languages(item)
        elif check_type == "audio":
            existing_langs = LanguageDetector.extract_audio_languages(item)
        else:
            raise ValueError(f"Invalid check_type: {check_type}")

        # Normalize required languages
        required_normalized = [lang.lower() for lang in required_langs]

        # Find missing languages
        missing = [
            lang for lang in required_normalized if lang not in existing_langs
        ]

        logger.debug(
            f"Item {item.name}: existing {check_type}s={existing_langs}, "
            f"required={required_normalized}, missing={missing}"
        )

        return sorted(missing)

    @staticmethod
    def infer_primary_language(item: JellyfinItem) -> str:
        """
        Infer the primary language of a media item.

        Uses heuristics:
        1. First default audio track language
        2. First audio track language
        3. First subtitle language
        4. Fall back to "en"

        Args:
            item: Jellyfin item

        Returns:
            Inferred BCP-47 language code
        """
        # Try to find default audio track
        for source in item.media_sources:
            for stream in source.media_streams:
                if stream.type.lower() == "audio" and stream.is_default:
                    lang = normalize_language_code(stream.language, stream.language_tag)
                    if lang != "und":
                        logger.debug(f"Inferred primary language from default audio: {lang}")
                        return lang

        # Try first audio track
        for source in item.media_sources:
            for stream in source.media_streams:
                if stream.type.lower() == "audio":
                    lang = normalize_language_code(stream.language, stream.language_tag)
                    if lang != "und":
                        logger.debug(f"Inferred primary language from first audio: {lang}")
                        return lang

        # Try first subtitle
        for source in item.media_sources:
            for stream in source.media_streams:
                if stream.type.lower() == "subtitle":
                    lang = normalize_language_code(stream.language, stream.language_tag)
                    if lang != "und":
                        logger.debug(f"Inferred primary language from first subtitle: {lang}")
                        return lang

        # Default to English
        logger.debug("Could not infer primary language, defaulting to 'en'")
        return "en"

    @staticmethod
    def should_process_item(item: JellyfinItem) -> bool:
        """
        Determine if an item should be processed for subtitle translation.

        Filters out non-media items and items without video streams.

        Args:
            item: Jellyfin item

        Returns:
            True if item should be processed
        """
        # Only process video content
        if item.type not in ("Movie", "Episode", "Video"):
            logger.debug(f"Skipping non-video item: {item.type}")
            return False

        # Must have at least one media source
        if not item.media_sources:
            logger.debug(f"Skipping item without media sources: {item.name}")
            return False

        # Must have at least one video stream
        has_video = False
        for source in item.media_sources:
            for stream in source.media_streams:
                if stream.type.lower() == "video":
                    has_video = True
                    break
            if has_video:
                break

        if not has_video:
            logger.debug(f"Skipping item without video stream: {item.name}")
            return False

        return True
