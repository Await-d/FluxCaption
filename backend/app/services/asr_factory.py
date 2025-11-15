"""
ASR Factory for selecting and creating ASR service instances.

Provides a unified interface to switch between different ASR engines
(faster-whisper, FunASR) based on configuration.
"""

from collections.abc import Callable
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# ASR Protocol (Interface)
# =============================================================================


class ASRProtocol(Protocol):
    """
    Protocol defining the ASR service interface.

    All ASR implementations must implement these methods.
    """

    def load_model(self) -> None:
        """Load ASR model into memory."""
        ...

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
        """Transcribe audio file to text with timestamps."""
        ...

    def transcribe_to_srt(
        self,
        audio_path: str,
        output_path: str,
        language: str | None = None,
        **kwargs,
    ) -> dict:
        """Transcribe audio and save as SRT subtitle."""
        ...

    def transcribe_to_vtt(
        self,
        audio_path: str,
        output_path: str,
        language: str | None = None,
        **kwargs,
    ) -> dict:
        """Transcribe audio and save as VTT subtitle."""
        ...

    def unload_model(self) -> None:
        """Unload model from memory to free resources."""
        ...


# =============================================================================
# ASR Engine Enum
# =============================================================================


class ASREngine:
    """ASR engine types."""

    FASTER_WHISPER = "faster-whisper"
    FUNASR = "funasr"


# =============================================================================
# ASR Factory
# =============================================================================


class ASRFactory:
    """
    Factory for creating ASR service instances.

    Selects the appropriate ASR engine based on configuration.
    """

    @staticmethod
    def create_asr_service(
        engine: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
        **kwargs,
    ) -> ASRProtocol:
        """
        Create an ASR service instance based on the specified engine.

        Args:
            engine: ASR engine to use ("faster-whisper" or "funasr")
                   If None, uses settings.asr_engine
            model_name: Model name/path (engine-specific)
            device: Device to use (cuda, cpu, auto)
            **kwargs: Additional engine-specific parameters

        Returns:
            ASR service instance implementing ASRProtocol

        Raises:
            ValueError: Unknown ASR engine
            ImportError: ASR engine library not installed
        """
        # Use configured engine if not specified
        engine = engine or getattr(settings, "asr_engine", ASREngine.FASTER_WHISPER)

        logger.info(f"Creating ASR service with engine: {engine}")

        if engine == ASREngine.FASTER_WHISPER:
            from app.services.asr_service import ASRService

            return ASRService(
                model_name=model_name,
                device=device,
                compute_type=kwargs.get("compute_type"),
                download_root=kwargs.get("download_root"),
            )

        elif engine == ASREngine.FUNASR:
            from app.services.funasr_service import FunASRService

            return FunASRService(
                model_name=model_name,
                device=device,
                download_root=kwargs.get("download_root"),
            )

        else:
            raise ValueError(
                f"Unknown ASR engine: {engine}. "
                f"Supported engines: {ASREngine.FASTER_WHISPER}, {ASREngine.FUNASR}"
            )

    @staticmethod
    def get_default_asr_service() -> ASRProtocol:
        """
        Get the default ASR service based on global settings.

        Returns:
            Default ASR service instance
        """
        return ASRFactory.create_asr_service()

    @staticmethod
    def get_available_engines() -> list[str]:
        """
        Get list of available ASR engines.

        Returns:
            List of engine names that can be instantiated
        """
        available = []

        # Check faster-whisper
        try:
            import faster_whisper

            available.append(ASREngine.FASTER_WHISPER)
        except ImportError:
            pass

        # Check FunASR
        try:
            import funasr

            available.append(ASREngine.FUNASR)
        except ImportError:
            pass

        return available

    @staticmethod
    def validate_engine(engine: str) -> bool:
        """
        Check if the specified engine is available.

        Args:
            engine: Engine name to validate

        Returns:
            True if engine is available, False otherwise
        """
        return engine in ASRFactory.get_available_engines()


# =============================================================================
# Global ASR Service Instance
# =============================================================================

_global_asr_service: ASRProtocol | None = None


def get_asr_service(engine: str | None = None, force_new: bool = False) -> ASRProtocol:
    """
    Get the global ASR service instance.

    Args:
        engine: ASR engine to use (None for default)
        force_new: Force creation of new instance

    Returns:
        ASR service instance
    """
    global _global_asr_service

    if force_new or _global_asr_service is None:
        _global_asr_service = ASRFactory.create_asr_service(engine=engine)

    return _global_asr_service


def reset_asr_service():
    """Reset the global ASR service instance."""
    global _global_asr_service
    if _global_asr_service is not None:
        _global_asr_service.unload_model()
        _global_asr_service = None
