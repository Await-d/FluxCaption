"""
Pydantic schemas for ASR (Automatic Speech Recognition) operations.

Defines request/response models for ASR endpoints and tasks.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# ASR Request Models
# =============================================================================

class ASRRequest(BaseModel):
    """
    Request to create an ASR task.
    """
    media_path: str = Field(..., description="Path to media file (video/audio)")
    language: Optional[str] = Field(None, description="Source language code (None for auto-detect)")
    output_format: str = Field(default="srt", description="Output subtitle format (srt, vtt)")
    vad_filter: bool = Field(default=True, description="Enable voice activity detection")
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="VAD threshold")

    # Optional: immediate translation
    translate_to: Optional[list[str]] = Field(None, description="Target languages for translation")
    mt_model: Optional[str] = Field(None, description="Translation model to use")


class ASRSegmentRequest(BaseModel):
    """
    Request to transcribe a specific segment of media.
    """
    media_path: str = Field(..., description="Path to media file")
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    duration: float = Field(..., gt=0, description="Duration in seconds")
    language: Optional[str] = Field(None, description="Source language")
    output_format: str = Field(default="srt", description="Output format")


# =============================================================================
# ASR Response Models
# =============================================================================

class TranscriptionSegment(BaseModel):
    """
    A single transcription segment.
    """
    id: int = Field(..., description="Segment ID")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text")
    avg_logprob: Optional[float] = Field(None, description="Average log probability")
    no_speech_prob: Optional[float] = Field(None, description="No speech probability")


class TranscriptionInfo(BaseModel):
    """
    Metadata about transcription.
    """
    language: str = Field(..., description="Detected/specified language")
    language_probability: float = Field(..., description="Language detection confidence")
    duration: float = Field(..., description="Audio duration in seconds")
    duration_after_vad: Optional[float] = Field(None, description="Duration after VAD filtering")
    num_segments: int = Field(..., description="Number of segments")


class ASRResponse(BaseModel):
    """
    Response for ASR transcription.
    """
    task_id: str = Field(..., description="Celery task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Human-readable message")


class ASRResultResponse(BaseModel):
    """
    Response containing ASR results.
    """
    output_path: str = Field(..., description="Path to output subtitle file")
    format: str = Field(..., description="Output format")
    segments: list[TranscriptionSegment] = Field(..., description="Transcription segments")
    info: TranscriptionInfo = Field(..., description="Transcription metadata")


# =============================================================================
# ASR Configuration Models
# =============================================================================

class ASRConfig(BaseModel):
    """
    ASR service configuration.
    """
    model: str = Field(..., description="Whisper model name")
    device: str = Field(..., description="Compute device (cuda/cpu)")
    compute_type: str = Field(..., description="Compute type (int8/float16)")
    vad_enabled: bool = Field(..., description="VAD enabled by default")
    vad_threshold: float = Field(..., description="Default VAD threshold")
    beam_size: int = Field(..., description="Beam size for decoding")


class ASRModelInfo(BaseModel):
    """
    Information about available ASR models.
    """
    name: str = Field(..., description="Model name")
    size: str = Field(..., description="Model size (tiny/base/small/medium/large)")
    parameters: str = Field(..., description="Number of parameters")
    multilingual: bool = Field(..., description="Supports multiple languages")
    loaded: bool = Field(..., description="Currently loaded in memory")
