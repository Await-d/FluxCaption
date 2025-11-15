"""
Subtitle parsing service.

Provides unified parsing for SRT, ASS, and VTT subtitle formats.
"""

from pathlib import Path
from typing import Any

import pysubs2

from app.core.logging import get_logger

logger = get_logger(__name__)


class SubtitleEntry:
    """Represents a single subtitle entry."""

    def __init__(
        self,
        index: int,
        start_ms: int,
        end_ms: int,
        text: str,
        style: str | None = None,
    ):
        self.index = index
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.text = text
        self.style = style

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "index": self.index,
            "start": self._format_time(self.start_ms),
            "end": self._format_time(self.end_ms),
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text": self.text,
            "style": self.style,
        }

    @staticmethod
    def _format_time(ms: int) -> str:
        """Format milliseconds to HH:MM:SS,mmm format."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


class SubtitleParser:
    """
    Parser for subtitle files.

    Supports SRT, ASS, and VTT formats using pysubs2.
    """

    @staticmethod
    def parse(
        file_path: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """
        Parse a subtitle file.

        Args:
            file_path: Path to subtitle file
            limit: Maximum number of entries to return
            offset: Number of entries to skip from beginning

        Returns:
            Dictionary containing:
                - format: File format (srt, ass, vtt)
                - total_lines: Total number of subtitle entries
                - entries: List of subtitle entries
                - has_more: Whether there are more entries

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        # Detect format from extension
        suffix = path.suffix.lower()
        if suffix == ".srt":
            format_type = "srt"
        elif suffix == ".ass":
            format_type = "ass"
        elif suffix == ".vtt":
            format_type = "vtt"
        else:
            raise ValueError(f"Unsupported subtitle format: {suffix}")

        logger.info(f"Parsing subtitle file: {file_path} (format={format_type})")

        try:
            # Load subtitle file
            subs = pysubs2.load(file_path)

            # Get total count
            total_lines = len(subs)

            # Apply pagination
            start_idx = offset or 0
            end_idx = start_idx + limit if limit else total_lines

            # Extract entries
            entries = []
            for idx, event in enumerate(subs[start_idx:end_idx], start=start_idx):
                entry = SubtitleEntry(
                    index=idx + 1,
                    start_ms=event.start,
                    end_ms=event.end,
                    text=event.text,
                    style=event.style if hasattr(event, "style") else None,
                )
                entries.append(entry.to_dict())

            has_more = end_idx < total_lines

            logger.info(
                f"Parsed {len(entries)} entries (total={total_lines}, "
                f"offset={start_idx}, has_more={has_more})"
            )

            return {
                "format": format_type,
                "total_lines": total_lines,
                "entries": entries,
                "has_more": has_more,
                "offset": start_idx,
                "limit": len(entries),
            }

        except Exception as e:
            logger.error(f"Failed to parse subtitle file {file_path}: {e}", exc_info=True)
            raise ValueError(f"Failed to parse subtitle: {str(e)}")

    @staticmethod
    def get_subtitle_info(file_path: str) -> dict[str, Any]:
        """
        Get basic information about a subtitle file without parsing all entries.

        Args:
            file_path: Path to subtitle file

        Returns:
            Dictionary containing basic subtitle info
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".srt":
            format_type = "srt"
        elif suffix == ".ass":
            format_type = "ass"
        elif suffix == ".vtt":
            format_type = "vtt"
        else:
            raise ValueError(f"Unsupported subtitle format: {suffix}")

        try:
            subs = pysubs2.load(file_path)
            total_lines = len(subs)

            # Get duration (last subtitle end time)
            duration_ms = subs[-1].end if subs else 0

            return {
                "format": format_type,
                "total_lines": total_lines,
                "duration_ms": duration_ms,
                "duration": SubtitleEntry._format_time(duration_ms),
            }

        except Exception as e:
            logger.error(f"Failed to get subtitle info for {file_path}: {e}")
            raise ValueError(f"Failed to get subtitle info: {str(e)}")
