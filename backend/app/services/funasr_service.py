"""
Automatic Speech Recognition (ASR) service using FunASR.

FunASR is an open-source speech recognition toolkit from ModelScope.
Provides transcription with support for multiple models and languages.
"""

from collections.abc import Callable
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Exceptions
# =============================================================================


class ASRError(Exception):
    """Base exception for ASR errors."""

    pass


class ModelLoadError(ASRError):
    """Model loading failed."""

    pass


class TranscriptionError(ASRError):
    """Transcription failed."""

    pass


# =============================================================================
# FunASR Service
# =============================================================================


class FunASRService:
    """
    ASR service using FunASR.

    Provides transcription with support for multiple FunASR models
    including Paraformer and SenseVoice models.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        download_root: str | None = None,
    ):
        """
        Initialize FunASR service.

        Args:
            model_name: FunASR model name (e.g., paraformer-zh, sensevoicesmall)
            device: Device to use (cuda, cpu)
            download_root: Directory to store models
        """
        # Default to paraformer-zh for Chinese/multilingual support
        self.model_name = model_name or getattr(settings, "funasr_model", "paraformer-zh")
        self.device = device or getattr(settings, "funasr_device", "cpu")
        self.download_root = download_root or getattr(
            settings, "funasr_model_cache_dir", "./models/funasr"
        )

        self.model = None
        logger.info(f"FunASR service initialized (model={self.model_name}, device={self.device})")

    def load_model(self):
        """
        Load FunASR model into memory.

        Raises:
            ModelLoadError: Model loading failed
        """
        if self.model is not None:
            logger.debug("Model already loaded")
            return

        try:
            from funasr import AutoModel

            logger.info(f"Loading FunASR model: {self.model_name}")

            # Create cache directory
            if self.download_root:
                Path(self.download_root).mkdir(parents=True, exist_ok=True)

            # Load model with AutoModel
            self.model = AutoModel(
                model=self.model_name,
                device=self.device,
                model_revision="v2.0.4",  # Use stable version
                cache_dir=self.download_root,
            )

            logger.info(f"FunASR model loaded successfully: {self.model_name}")

        except ImportError:
            raise ModelLoadError("FunASR not installed. Install: pip install funasr")
        except Exception as e:
            raise ModelLoadError(f"Failed to load FunASR model {self.model_name}: {e}")

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        task: str = "transcribe",
        vad_filter: bool = True,
        vad_threshold: float = 0.5,
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[dict], dict]:
        """
        Transcribe audio file to text with timestamps.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Source language code (None for auto-detect)
            task: Task type ("transcribe" or "translate")
            vad_filter: Use voice activity detection (not used in FunASR)
            vad_threshold: VAD threshold (not used in FunASR)
            beam_size: Beam size for decoding (not used in FunASR)
            best_of: Number of candidates when sampling (not used in FunASR)
            temperature: Temperature for sampling (not used in FunASR)
            progress_callback: Optional callback(completed, total)

        Returns:
            Tuple of (segments, info)
            - segments: List of segment dicts with text, start, end
            - info: Transcription metadata

        Raises:
            TranscriptionError: Transcription failed
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        # Load model if not already loaded
        if self.model is None:
            self.load_model()

        logger.info(f"Transcribing with FunASR: {audio_path} (language={language or 'auto'})")

        try:
            # Prepare generation parameters
            generate_kwargs = {}
            if language:
                # Map common language codes to FunASR format
                lang_map = {
                    "zh": "zh",
                    "zh-CN": "zh",
                    "en": "en",
                    "ja": "ja",
                    "ko": "ko",
                }
                funasr_lang = lang_map.get(language, language)
                generate_kwargs["language"] = funasr_lang

            # Run inference
            result = self.model.generate(
                input=str(audio_file),
                batch_size_s=300,  # Process in chunks of 300 seconds
                **generate_kwargs,
            )

            # Parse FunASR result
            segments = []
            detected_language = language or "zh"  # Default to Chinese if not specified

            if isinstance(result, list) and len(result) > 0:
                # FunASR returns list of results
                for res in result:
                    if "text" in res:
                        # Extract timestamps if available
                        if "timestamp" in res and res["timestamp"]:
                            # Format: [[start_ms, end_ms], ...]
                            for idx, (start_ms, end_ms) in enumerate(res["timestamp"]):
                                # Extract corresponding text segment
                                # This is approximate - FunASR timestamp format varies
                                segment_text = res["text"] if idx == 0 else ""

                                segments.append(
                                    {
                                        "id": idx,
                                        "start": start_ms / 1000.0,  # Convert ms to seconds
                                        "end": end_ms / 1000.0,
                                        "text": segment_text.strip(),
                                        "words": None,
                                        "avg_logprob": 0.0,
                                        "no_speech_prob": 0.0,
                                    }
                                )
                        else:
                            # No timestamps, create single segment
                            segments.append(
                                {
                                    "id": 0,
                                    "start": 0.0,
                                    "end": 0.0,
                                    "text": res["text"].strip(),
                                    "words": None,
                                    "avg_logprob": 0.0,
                                    "no_speech_prob": 0.0,
                                }
                            )

                        # Update detected language if available
                        if "lang" in res:
                            detected_language = res["lang"]

            # If no segments were created, create a fallback
            if not segments and result:
                # Try to extract text directly
                text = str(result[0].get("text", "")) if isinstance(result, list) else str(result)
                if text:
                    segments.append(
                        {
                            "id": 0,
                            "start": 0.0,
                            "end": 0.0,
                            "text": text.strip(),
                            "words": None,
                            "avg_logprob": 0.0,
                            "no_speech_prob": 0.0,
                        }
                    )

            # Progress callback
            if progress_callback:
                progress_callback(len(segments), len(segments))

            # Calculate approximate duration from last segment
            duration = segments[-1]["end"] if segments and segments[-1]["end"] > 0 else 0.0

            logger.info(
                f"FunASR transcription complete: {len(segments)} segments, "
                f"language={detected_language}, duration={duration:.2f}s"
            )

            # Build info dict
            info_dict = {
                "language": detected_language,
                "language_probability": 1.0,  # FunASR doesn't provide this
                "duration": duration,
                "duration_after_vad": None,
                "all_language_probs": None,
            }

            return segments, info_dict

        except Exception as e:
            logger.error(f"FunASR transcription failed: {e}", exc_info=True)
            raise TranscriptionError(f"FunASR transcription failed: {e}")

    def transcribe_to_srt(
        self,
        audio_path: str,
        output_path: str,
        language: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Transcribe audio and save as SRT subtitle.

        Args:
            audio_path: Path to audio file
            output_path: Path to output SRT file
            language: Source language (None for auto-detect)
            **kwargs: Additional arguments for transcribe()

        Returns:
            Transcription info dict

        Raises:
            TranscriptionError: Transcription failed
        """
        logger.info(f"Transcribing with FunASR {audio_path} to SRT: {output_path}")

        # Transcribe
        segments, info = self.transcribe(audio_path, language=language, **kwargs)

        # Generate SRT content
        srt_content = self._segments_to_srt(segments)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(srt_content, encoding="utf-8")

        logger.info(f"SRT file written: {output_path} ({len(segments)} segments)")

        return {
            "output_path": str(output_file),
            "num_segments": len(segments),
            "language": info["language"],
            "duration": info["duration"],
        }

    def transcribe_to_vtt(
        self,
        audio_path: str,
        output_path: str,
        language: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Transcribe audio and save as VTT subtitle.

        Args:
            audio_path: Path to audio file
            output_path: Path to output VTT file
            language: Source language (None for auto-detect)
            **kwargs: Additional arguments for transcribe()

        Returns:
            Transcription info dict
        """
        logger.info(f"Transcribing with FunASR {audio_path} to VTT: {output_path}")

        # Transcribe
        segments, info = self.transcribe(audio_path, language=language, **kwargs)

        # Generate VTT content
        vtt_content = self._segments_to_vtt(segments)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(vtt_content, encoding="utf-8")

        logger.info(f"VTT file written: {output_path} ({len(segments)} segments)")

        return {
            "output_path": str(output_file),
            "num_segments": len(segments),
            "language": info["language"],
            "duration": info["duration"],
        }

    def _segments_to_srt(self, segments: list[dict]) -> str:
        """
        Convert segments to SRT format.

        Args:
            segments: List of segment dicts

        Returns:
            SRT formatted string
        """
        srt_lines = []

        for i, segment in enumerate(segments, start=1):
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            # Format timestamps (HH:MM:SS,mmm)
            start_time = self._seconds_to_srt_time(start)
            end_time = self._seconds_to_srt_time(end)

            # SRT format
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")  # Blank line

        return "\n".join(srt_lines)

    def _segments_to_vtt(self, segments: list[dict]) -> str:
        """
        Convert segments to VTT format.

        Args:
            segments: List of segment dicts

        Returns:
            VTT formatted string
        """
        vtt_lines = ["WEBVTT", ""]

        for segment in segments:
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            # Format timestamps (HH:MM:SS.mmm)
            start_time = self._seconds_to_vtt_time(start)
            end_time = self._seconds_to_vtt_time(end)

            # VTT format
            vtt_lines.append(f"{start_time} --> {end_time}")
            vtt_lines.append(text)
            vtt_lines.append("")  # Blank line

        return "\n".join(vtt_lines)

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        """Convert seconds to VTT time format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def unload_model(self):
        """Unload model from memory to free resources."""
        if self.model is not None:
            logger.info("Unloading FunASR model")
            self.model = None


# =============================================================================
# Singleton Instance
# =============================================================================

_funasr_service: FunASRService | None = None


def get_funasr_service() -> FunASRService:
    """
    Get global FunASR service instance.

    Returns:
        Shared FunASRService instance
    """
    global _funasr_service
    if _funasr_service is None:
        _funasr_service = FunASRService()
    return _funasr_service
