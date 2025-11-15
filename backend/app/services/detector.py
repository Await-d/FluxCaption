"""
Missing language detection service.

Analyzes Jellyfin media items to determine which subtitle languages are missing
based on configured requirements.
"""

from app.core.logging import get_logger
from app.schemas.jellyfin import JellyfinItem

logger = get_logger(__name__)


# =============================================================================
# Language Code Normalization
# =============================================================================

# ISO 639-2 (3-letter) to BCP-47 mapping
# Comprehensive mapping to support more languages from Jellyfin
ISO639_2_TO_BCP47 = {
    # English
    "eng": "en",
    # Chinese variants
    "chi": "zh-CN",  # Simplified Chinese (default)
    "zho": "zh-CN",  # Chinese
    "cmn": "zh-CN",  # Mandarin Chinese
    "yue": "zh-HK",  # Cantonese
    # Japanese
    "jpn": "ja",
    # Korean
    "kor": "ko",
    # French
    "fre": "fr",
    "fra": "fr",
    # German
    "ger": "de",
    "deu": "de",
    # Spanish
    "spa": "es",
    # Russian
    "rus": "ru",
    # Italian
    "ita": "it",
    # Portuguese
    "por": "pt",
    # Arabic
    "ara": "ar",
    # Hindi
    "hin": "hi",
    # Thai
    "tha": "th",
    # Vietnamese
    "vie": "vi",
    # Polish
    "pol": "pl",
    # Dutch
    "dut": "nl",
    "nld": "nl",
    # Turkish
    "tur": "tr",
    # Swedish
    "swe": "sv",
    # Danish
    "dan": "da",
    # Norwegian
    "nor": "no",
    "nob": "nb",  # Norwegian Bokmål
    "nno": "nn",  # Norwegian Nynorsk
    # Finnish
    "fin": "fi",
    # Greek
    "gre": "el",
    "ell": "el",
    # Hebrew
    "heb": "he",
    # Czech
    "cze": "cs",
    "ces": "cs",
    # Romanian
    "rum": "ro",
    "ron": "ro",
    # Hungarian
    "hun": "hu",
    # Indonesian
    "ind": "id",
    # Malay
    "may": "ms",
    "msa": "ms",
    # Ukrainian
    "ukr": "uk",
    # Bulgarian
    "bul": "bg",
    # Croatian
    "hrv": "hr",
    # Serbian
    "srp": "sr",
    # Slovak
    "slo": "sk",
    "slk": "sk",
    # Slovenian
    "slv": "sl",
    # Lithuanian
    "lit": "lt",
    # Latvian
    "lav": "lv",
    # Estonian
    "est": "et",
    # Catalan
    "cat": "ca",
    # Basque
    "baq": "eu",
    "eus": "eu",
    # Galician
    "glg": "gl",
    # Icelandic
    "ice": "is",
    "isl": "is",
    # Persian/Farsi
    "per": "fa",
    "fas": "fa",
    # Bengali
    "ben": "bn",
    # Urdu
    "urd": "ur",
    # Tamil
    "tam": "ta",
    # Telugu
    "tel": "te",
    # Marathi
    "mar": "mr",
    # Kannada
    "kan": "kn",
    # Malayalam
    "mal": "ml",
    # Punjabi
    "pan": "pa",
    # Gujarati
    "guj": "gu",
}


def get_required_langs_from_rules(db_session=None) -> list[str]:
    """
    从启用的自动翻译规则中推断需要检测的语言列表。

    如果有自动翻译规则，则从规则中提取所有目标语言作为检测目标。
    如果没有规则，返回默认的常用语言列表。

    Args:
        db_session: Optional database session

    Returns:
        list[str]: 需要检测的语言代码列表（BCP-47格式）
    """
    if not db_session:
        # 无数据库连接，返回默认语言
        logger.warning("No database session provided, using default languages")
        return ["zh-CN", "en", "ja"]

    try:
        import json

        from app.models.auto_translation_rule import AutoTranslationRule

        # 查询所有启用的自动翻译规则
        rules = db_session.query(AutoTranslationRule).filter(AutoTranslationRule.enabled).all()

        if not rules:
            # 没有规则，返回默认语言
            logger.info("No auto translation rules found, using default languages")
            return ["zh-CN", "en", "ja"]

        # 从规则中提取所有目标语言
        target_langs = set()
        for rule in rules:
            try:
                langs = json.loads(rule.target_langs)
                target_langs.update(langs)
            except Exception as e:
                logger.warning(f"Failed to parse target_langs from rule {rule.id}: {e}")
                continue

        if not target_langs:
            # 规则中没有目标语言，返回默认语言
            logger.warning("No target languages found in rules, using default languages")
            return ["zh-CN", "en", "ja"]

        result = sorted(target_langs)
        logger.info(f"Inferred required languages from {len(rules)} rules: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to get required languages from rules: {e}", exc_info=True)
        # 出错时返回默认语言
        return ["zh-CN", "en", "ja"]


def normalize_language_code(language: str | None, language_tag: str | None = None) -> str:
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

        return sorted(languages)

    @staticmethod
    def extract_subtitle_streams(item: JellyfinItem) -> list[dict]:
        """
        Extract all subtitle stream information from a Jellyfin item.

        Unlike extract_subtitle_languages(), this method returns complete information
        about each subtitle stream, including duplicate languages.

        Args:
            item: Jellyfin item with MediaSources

        Returns:
            List of subtitle stream dictionaries with keys:
            - index: Stream index
            - language: Normalized BCP-47 language code
            - display_title: Human-readable title
            - codec: Subtitle codec (srt, ass, etc.)
            - is_default: Whether this is the default subtitle
            - is_forced: Whether this is a forced subtitle
            - is_external: Whether this is an external/sidecar subtitle

        Example:
            >>> item = JellyfinItem(...)
            >>> streams = LanguageDetector.extract_subtitle_streams(item)
            >>> streams
            [
                {
                    'index': 2,
                    'language': 'zh-CN',
                    'display_title': 'Chi - 默认 - SUBRIP',
                    'codec': 'subrip',
                    'is_default': True,
                    'is_forced': False,
                    'is_external': False
                },
                {
                    'index': 3,
                    'language': 'zh-CN',
                    'display_title': 'Chi - SUBRIP',
                    'codec': 'subrip',
                    'is_default': False,
                    'is_forced': False,
                    'is_external': False
                }
            ]
        """
        streams = []

        for source in item.media_sources:
            for stream in source.media_streams:
                if stream.type.lower() != "subtitle":
                    continue

                # Normalize language code
                lang = normalize_language_code(stream.language, stream.language_tag)

                # Skip undefined languages
                if lang == "und":
                    continue

                streams.append(
                    {
                        "index": stream.index,
                        "language": lang,
                        "display_title": stream.display_title or f"{lang.upper()} subtitle",
                        "codec": stream.codec or "unknown",
                        "is_default": stream.is_default,
                        "is_forced": stream.is_forced,
                        "is_external": stream.is_external,
                    }
                )

        # Sort by index to maintain original order
        return sorted(streams, key=lambda x: x["index"])

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

        return sorted(languages)

    @staticmethod
    def detect_missing_languages(
        item: JellyfinItem,
        required_langs: list[str],
        check_type: str = "subtitle",
        db_session=None,
    ) -> list[str]:
        """
        Detect which required languages are missing from an item.

        Checks both Jellyfin streams AND database records to avoid re-translating.

        Args:
            item: Jellyfin item to analyze
            required_langs: List of required BCP-47 language codes
            check_type: Type to check - "subtitle" or "audio"
            db_session: Optional database session to check for existing subtitles

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

        # Also check database for generated subtitles
        if db_session and check_type == "subtitle":
            from app.models.media_asset import MediaAsset
            from app.models.subtitle import Subtitle

            # Find asset by item_id
            asset = db_session.query(MediaAsset).filter_by(item_id=item.id).first()
            if asset:
                # Get all subtitle languages from database
                db_subtitles = db_session.query(Subtitle).filter_by(asset_id=asset.id).all()
                db_langs = {sub.lang.lower() for sub in db_subtitles}

                # Merge with existing languages
                existing_langs = list(set(existing_langs) | db_langs)

                logger.debug(
                    f"Item {item.name}: found {len(db_langs)} subtitles in database: {sorted(db_langs)}"
                )

        # Normalize required languages
        required_normalized = [lang.lower() for lang in required_langs]

        # Find missing languages
        missing = [lang for lang in required_normalized if lang not in existing_langs]

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
