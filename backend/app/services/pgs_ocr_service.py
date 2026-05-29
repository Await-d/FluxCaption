"""
PGS/SUP OCR service.

Converts image-based Blu-ray subtitles into text subtitles before translation.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PGSOcrError(RuntimeError):
    """Raised when PGS OCR preprocessing fails."""


class PGSOcrService:
    """OCR conversion for `.sup`/PGS subtitles."""

    LANGUAGE_HINTS = {
        "en": ["eng"],
        "zh": ["zh"],
        "zh-cn": ["zh"],
        "zh-tw": ["zh"],
        "ja": ["ja"],
        "ko": ["ko"],
        "fr": ["fr"],
        "de": ["de"],
        "es": ["es"],
        "pt": ["pt"],
        "ru": ["ru"],
        "it": ["it"],
    }

    @staticmethod
    def is_pgs_subtitle(file_path: str) -> bool:
        return Path(file_path).suffix.lower() == ".sup"

    @staticmethod
    def resolve_engine() -> str:
        engine = settings.pgs_ocr_engine
        if engine == "disabled":
            raise PGSOcrError("PGS OCR is disabled. Enable an OCR engine in settings first.")

        if engine == "pgsocr":
            if shutil.which(settings.pgsocr_executable):
                return "pgsocr"
            if PGSOcrService._can_run_module_command():
                return "pgsocr"
            raise PGSOcrError(
                f"Configured OCR engine '{settings.pgsocr_executable}' was not found in PATH."
            )

        if engine == "subtitleedit":
            if shutil.which(settings.subtitle_edit_executable):
                return "subtitleedit"
            raise PGSOcrError(
                f"Configured OCR engine '{settings.subtitle_edit_executable}' was not found in PATH."
            )

        if shutil.which(settings.pgsocr_executable):
            return "pgsocr"
        if PGSOcrService._can_run_module_command():
            return "pgsocr"
        if shutil.which(settings.subtitle_edit_executable):
            return "subtitleedit"

        raise PGSOcrError(
            "No available PGS OCR engine found. Install `pgsocr` or Subtitle Edit, "
            "or configure `pgs_ocr_engine=disabled` to block SUP uploads."
        )

    @classmethod
    def ocr_subtitle(
        cls,
        input_path: str,
        output_dir: str,
        source_lang: str | None = None,
        output_format: str | None = None,
    ) -> dict:
        input_file = Path(input_path)
        if not input_file.exists():
            raise PGSOcrError(f"PGS subtitle not found: {input_path}")

        if input_file.suffix.lower() != ".sup":
            raise PGSOcrError(f"Unsupported PGS subtitle input: {input_file.suffix}")

        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        resolved_format = (output_format or settings.pgs_ocr_output_format).lower()
        if resolved_format not in {"srt", "ass"}:
            raise PGSOcrError(f"Unsupported OCR output format: {resolved_format}")

        output_path = output_directory / f"{input_file.stem}.{resolved_format}"
        engine = cls.resolve_engine()

        logger.info(
            f"Starting PGS OCR: {input_file} -> {output_path} (engine={engine}, source_lang={source_lang})"
        )

        if engine == "pgsocr":
            cls._run_pgsocr(input_file, output_directory, source_lang, resolved_format)
        else:
            cls._run_subtitle_edit(input_file, output_directory, resolved_format)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PGSOcrError(f"OCR completed but no output file was produced: {output_path}")

        return {
            "engine": engine,
            "input_path": str(input_file),
            "output_path": str(output_path),
            "output_format": resolved_format,
        }

    @classmethod
    def _run_pgsocr(
        cls,
        input_file: Path,
        output_directory: Path,
        source_lang: str | None,
        output_format: str,
    ) -> None:
        command = [
            *cls._build_pgsocr_command_prefix(),
            "-i",
            str(input_file),
            "-o",
            str(output_directory),
            "-m",
            "tesseract",
            "-f",
            output_format.upper(),
        ]

        language_hints = cls._map_language_hint(source_lang)
        if language_hints:
            command.extend(["-l", *language_hints])

        cls._run_command(command, f"pgsocr conversion for {input_file.name}")

    @classmethod
    def _run_subtitle_edit(cls, input_file: Path, output_directory: Path, output_format: str) -> None:
        command = [
            settings.subtitle_edit_executable,
            "/convert",
            str(input_file),
            output_format,
            f"/outputfolder:{output_directory}",
        ]
        cls._run_command(command, f"Subtitle Edit conversion for {input_file.name}")

    @staticmethod
    def _run_command(command: list[str], description: str) -> None:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.pgs_ocr_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PGSOcrError(f"{description} timed out after {settings.pgs_ocr_timeout_seconds}s") from exc
        except OSError as exc:
            raise PGSOcrError(f"Failed to start OCR engine for {description}: {exc}") from exc

        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise PGSOcrError(f"{description} failed: {stderr or f'exit code {result.returncode}'}")

    @staticmethod
    def _build_pgsocr_command_prefix() -> list[str]:
        if shutil.which(settings.pgsocr_executable):
            return [settings.pgsocr_executable]

        return shlex.split(settings.pgsocr_module_command, posix=False)

    @staticmethod
    def _can_run_module_command() -> bool:
        try:
            prefix = shlex.split(settings.pgsocr_module_command, posix=False)
            result = subprocess.run(
                [*prefix, "--help"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def _map_language_hint(cls, source_lang: str | None) -> list[str]:
        if not source_lang or source_lang == "auto":
            return []

        normalized = source_lang.lower()
        if normalized in cls.LANGUAGE_HINTS:
            return cls.LANGUAGE_HINTS[normalized]

        primary = normalized.split("-")[0]
        return cls.LANGUAGE_HINTS.get(primary, [])
