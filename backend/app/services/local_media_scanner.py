"""
Local media file scanner service.

Scans local directories for media files and detects subtitle availability.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MediaFile:
    """Represents a local media file with metadata."""

    path: str
    name: str
    extension: str
    size_bytes: int
    directory: str
    audio_languages: list[str]
    subtitle_languages: list[str]
    missing_languages: list[str]
    subtitle_files: list[str]

    @property
    def filepath(self) -> str:
        return self.path

    @property
    def filename(self) -> str:
        return self.name

    @property
    def existing_subtitle_langs(self) -> list[str]:
        return self.subtitle_languages


class LocalMediaScanner:
    """Scanner for local media files and subtitles."""

    # Supported video file extensions
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
        ".ogv",
        ".ts",
        ".m2ts",
    }

    # Supported subtitle extensions
    SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub", ".idx"}

    # Language code patterns in filenames (e.g., .zh-CN.srt, .en.srt)
    LANG_PATTERN = re.compile(r"\.([a-z]{2}(-[A-Z]{2})?)\.(srt|ass|ssa|vtt|sub)$", re.IGNORECASE)

    def __init__(self):
        """Initialize the local media scanner."""
        pass

    def scan_directory(
        self, directory: str, required_langs: list[str], recursive: bool = True, max_depth: int = 5
    ) -> list[MediaFile]:
        """
        Scan a directory for media files and analyze subtitle availability.

        Args:
            directory: Directory path to scan
            required_langs: List of required subtitle languages (e.g., ['zh-CN', 'en'])
            recursive: Whether to scan subdirectories recursively
            max_depth: Maximum recursion depth (防止无限递归)

        Returns:
            List of MediaFile objects with subtitle analysis

        Raises:
            ValueError: If directory doesn't exist or is not accessible
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        media_files = []

        # Scan for video files
        if recursive:
            video_files = self._scan_recursive(directory_path, max_depth)
        else:
            video_files = self._scan_single_directory(directory_path)

        # Analyze each video file
        for video_path in video_files:
            try:
                media_file = self._analyze_media_file(video_path, required_langs)
                media_files.append(media_file)
            except Exception as e:
                logger.warning(f"Failed to analyze {video_path}: {e}")
                continue

        logger.info(f"Scanned {directory}: found {len(media_files)} media files")
        return media_files

    def _scan_recursive(
        self, directory: Path, max_depth: int, current_depth: int = 0
    ) -> list[Path]:
        """Recursively scan directory for video files."""
        video_files = []

        if current_depth > max_depth:
            logger.warning(f"Reached max depth {max_depth} at {directory}")
            return video_files

        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix.lower() in self.VIDEO_EXTENSIONS:
                    video_files.append(item)
                elif item.is_dir():
                    # Skip hidden directories
                    if not item.name.startswith("."):
                        video_files.extend(self._scan_recursive(item, max_depth, current_depth + 1))
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory}: {e}")

        return video_files

    def _scan_single_directory(self, directory: Path) -> list[Path]:
        """Scan a single directory (non-recursive)."""
        video_files = []

        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix.lower() in self.VIDEO_EXTENSIONS:
                    video_files.append(item)
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory}: {e}")

        return video_files

    def _analyze_media_file(self, video_path: Path, required_langs: list[str]) -> MediaFile:
        """
        Analyze a media file and detect existing subtitles.

        Args:
            video_path: Path to video file
            required_langs: Required subtitle languages

        Returns:
            MediaFile object with analysis
        """
        # Get file metadata
        file_stat = video_path.stat()

        # Find existing subtitle files
        subtitle_langs, subtitle_files = self._find_subtitle_languages(video_path)

        # Detect audio languages via ffprobe (best-effort)
        audio_langs = self._detect_audio_languages(video_path)

        # Detect missing languages
        missing_langs = [lang for lang in required_langs if lang not in subtitle_langs]

        return MediaFile(
            path=str(video_path),
            name=video_path.name,
            extension=video_path.suffix,
            size_bytes=file_stat.st_size,
            directory=str(video_path.parent),
            audio_languages=audio_langs,
            subtitle_languages=subtitle_langs,
            missing_languages=missing_langs,
            subtitle_files=subtitle_files,
        )

    def _find_subtitle_languages(self, video_path: Path) -> tuple[list[str], list[str]]:
        """
        Find existing subtitle files for a video and extract language codes.

        Looks for subtitle files with naming patterns:
        - video.zh-CN.srt
        - video.en.srt
        - video.chs.ass (Chinese Simplified - maps to zh-CN)
        - video.cht.ass (Chinese Traditional - maps to zh-TW)

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (language codes, subtitle file paths)
        """
        subtitle_langs: set[str] = set()
        subtitle_files: list[str] = []
        video_stem = video_path.stem  # filename without extension
        video_dir = video_path.parent

        # Check for subtitle files with same base name
        for subtitle_path in video_dir.glob(f"{video_stem}*"):
            if subtitle_path.suffix.lower() in self.SUBTITLE_EXTENSIONS:
                subtitle_files.append(str(subtitle_path))
                # Try to extract language code from filename
                match = self.LANG_PATTERN.search(subtitle_path.name)
                if match:
                    lang_code = match.group(1)
                    subtitle_langs.add(lang_code)
                else:
                    # Check for common abbreviations
                    name_lower = subtitle_path.stem.lower()
                    if "chs" in name_lower or "chi" in name_lower or "sc" in name_lower:
                        subtitle_langs.add("zh-CN")
                    elif "cht" in name_lower or "tc" in name_lower:
                        subtitle_langs.add("zh-TW")
                    elif "eng" in name_lower or name_lower.endswith(".en"):
                        subtitle_langs.add("en")
                    elif "jpn" in name_lower or "jap" in name_lower or name_lower.endswith(".ja"):
                        subtitle_langs.add("ja")
                    elif "kor" in name_lower or name_lower.endswith(".ko"):
                        subtitle_langs.add("ko")

        return sorted(subtitle_langs), subtitle_files

    def _detect_audio_languages(self, video_path: Path) -> list[str]:
        """Detect audio languages using ffprobe (best-effort, non-fatal)."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index,codec_type:stream_tags=language",
            "-of",
            "json",
            str(video_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
        except FileNotFoundError:
            logger.warning("ffprobe not found; audio language detection skipped")
            return []
        except subprocess.CalledProcessError as exc:
            logger.warning(f"ffprobe failed for {video_path}: {exc.stderr or exc}")
            return []
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe timed out for {video_path}")
            return []

        try:
            data = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            logger.warning(f"Unable to parse ffprobe output for {video_path}")
            return []

        languages: set[str] = set()
        for stream in data.get("streams", []):
            tags = stream.get("tags") or {}
            lang = tags.get("language")
            if lang:
                normalized = self._normalize_language_code(str(lang))
                if normalized:
                    languages.add(normalized)

        return sorted(languages)

    @staticmethod
    def _normalize_language_code(lang: str) -> str | None:
        """Normalize ffprobe language codes to BCP-47 style when possible."""
        code = lang.strip().lower()
        # ISO 639-2 to 639-1 common mappings
        mapping = {
            "eng": "en",
            "en": "en",
            "zho": "zh-CN",
            "chi": "zh-CN",
            "cmn": "zh-CN",
            "zh": "zh-CN",
            "jpn": "ja",
            "ja": "ja",
            "kor": "ko",
            "ko": "ko",
            "spa": "es",
            "es": "es",
            "fra": "fr",
            "fre": "fr",
            "fr": "fr",
            "deu": "de",
            "ger": "de",
            "de": "de",
        }

        if code in mapping:
            return mapping[code]

        # Already looks like bcp-47 (e.g., en-US)
        if re.match(r"^[a-z]{2}(-[a-z]{2})?$", code):
            return code

        return None

    def get_directory_stats(self, directory: str, recursive: bool = True) -> dict:
        """
        Get statistics about a directory without full analysis.

        Args:
            directory: Directory path
            recursive: Whether to scan recursively

        Returns:
            Dictionary with stats
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        video_count = 0
        subtitle_count = 0
        total_size = 0

        if recursive:
            video_files = self._scan_recursive(directory_path, max_depth=5)
        else:
            video_files = self._scan_single_directory(directory_path)

        for video_path in video_files:
            video_count += 1
            total_size += video_path.stat().st_size

            # Count subtitle files
            video_stem = video_path.stem
            video_dir = video_path.parent
            for subtitle_path in video_dir.glob(f"{video_stem}*"):
                if subtitle_path.suffix.lower() in self.SUBTITLE_EXTENSIONS:
                    subtitle_count += 1

        return {
            "video_count": video_count,
            "subtitle_count": subtitle_count,
            "total_size_bytes": total_size,
            "directory": str(directory_path),
        }


# Global scanner instance
_scanner_instance = None


def get_local_media_scanner() -> LocalMediaScanner:
    """Get or create the global LocalMediaScanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = LocalMediaScanner()
    return _scanner_instance
