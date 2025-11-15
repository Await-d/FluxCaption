"""
Automatic Speech Recognition (ASR) service using faster-whisper.

Transcribes audio to text with timestamps for subtitle generation.
"""

from collections.abc import Callable
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy import to avoid loading model at module import time
_whisper_model = None


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
# ASR Service
# =============================================================================


class ASRService:
    """
    ASR service using faster-whisper.

    Provides transcription with automatic language detection,
    VAD filtering, and subtitle generation.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        download_root: str | None = None,
    ):
        """
        Initialize ASR service.

        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
            device: Device to use (cuda, cpu, auto)
            compute_type: Compute type (int8, int8_float16, float16)
            download_root: Directory to store models
        """
        self.model_name = model_name or settings.asr_model
        self.device = device or settings.asr_device
        self.compute_type = compute_type or settings.asr_compute_type
        self.download_root = download_root or settings.asr_model_cache_dir

        self.model = None
        logger.info(
            f"ASR service initialized (model={self.model_name}, "
            f"device={self.device}, compute_type={self.compute_type})"
        )

    def load_model(self):
        """
        Load Whisper model into memory.

        Raises:
            ModelLoadError: Model loading failed
        """
        if self.model is not None:
            logger.debug("Model already loaded")
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading Whisper model: {self.model_name}")

            # Create cache directory
            if self.download_root:
                Path(self.download_root).mkdir(parents=True, exist_ok=True)

            self.model = WhisperModel(
                model_size_or_path=self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.download_root,
                cpu_threads=settings.asr_num_workers,
            )

            logger.info(f"Model loaded successfully: {self.model_name}")

        except ImportError:
            raise ModelLoadError(
                "faster-whisper not installed. Install: pip install faster-whisper"
            )
        except Exception as e:
            raise ModelLoadError(f"Failed to load model {self.model_name}: {e}")

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
            vad_filter: Use voice activity detection
            vad_threshold: VAD threshold (0-1)
            beam_size: Beam size for decoding
            best_of: Number of candidates when sampling
            temperature: Temperature for sampling (0 for greedy)
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

        logger.info(
            f"Transcribing {audio_path} "
            f"(language={language or 'auto'}, task={task}, vad={vad_filter})"
        )

        try:
            # Prepare VAD parameters
            vad_params = None
            if vad_filter:
                vad_params = {
                    "threshold": vad_threshold,
                    "min_speech_duration_ms": 250,
                    "max_speech_duration_s": float("inf"),
                    "min_silence_duration_ms": 2000,
                }

            # Transcribe
            segments_iterator, info = self.model.transcribe(
                audio=str(audio_file),
                language=language,
                task=task,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                vad_filter=vad_filter,
                vad_parameters=vad_params,
            )

            # Convert iterator to list and track progress
            segments = []
            total_segments = 0

            for segment in segments_iterator:
                segments.append(
                    {
                        "id": segment.id,
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "words": getattr(segment, "words", None),
                        "avg_logprob": segment.avg_logprob,
                        "no_speech_prob": segment.no_speech_prob,
                    }
                )

                if progress_callback:
                    total_segments += 1
                    # Estimate total based on duration
                    # This is approximate since we don't know total in advance
                    progress_callback(total_segments, total_segments + 10)

            # Final progress update
            if progress_callback:
                progress_callback(total_segments, total_segments)

            logger.info(
                f"Transcription complete: {len(segments)} segments, "
                f"language={info.language}, duration={info.duration:.2f}s"
            )

            # Build info dict
            info_dict = {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "duration_after_vad": getattr(info, "duration_after_vad", None),
                "all_language_probs": getattr(info, "all_language_probs", None),
            }

            return segments, info_dict

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise TranscriptionError(f"Transcription failed: {e}")

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
        logger.info(f"Transcribing {audio_path} to SRT: {output_path}")

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
        logger.info(f"Transcribing {audio_path} to VTT: {output_path}")

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
            logger.info("Unloading ASR model")
            self.model = None


# =============================================================================
# Singleton Instance
# =============================================================================

_asr_service: ASRService | None = None


def get_asr_service() -> ASRService:
    """
    Get global ASR service instance.

    Returns:
        Shared ASRService instance
    """
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
