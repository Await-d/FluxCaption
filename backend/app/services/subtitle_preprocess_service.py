"""Preprocess subtitle inputs before translation."""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services.pgs_ocr_service import PGSOcrService


class SubtitlePreprocessService:
    """Prepare subtitle sources so the translation pipeline always receives text subtitles."""

    @staticmethod
    def prepare_for_translation(input_path: str, source_lang: str | None = None) -> dict:
        source_path = Path(input_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Subtitle source not found: {input_path}")

        if not PGSOcrService.is_pgs_subtitle(str(source_path)):
            return {
                "input_path": str(source_path),
                "output_path": str(source_path),
                "was_preprocessed": False,
                "format": source_path.suffix.lower().lstrip("."),
            }

        output_dir = Path(settings.temp_dir) / "pgs_ocr" / source_path.stem
        result = PGSOcrService.ocr_subtitle(
            input_path=str(source_path),
            output_dir=str(output_dir),
            source_lang=source_lang,
            output_format=settings.pgs_ocr_output_format,
        )
        result["was_preprocessed"] = True
        result["format"] = settings.pgs_ocr_output_format
        return result
