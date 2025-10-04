"""
Audio extraction service using FFmpeg.

Extracts audio from video files and converts to format suitable for ASR.
"""

import subprocess
from pathlib import Path
from typing import Optional, Callable
import tempfile
import shutil

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class AudioExtractionError(Exception):
    """Base exception for audio extraction errors."""
    pass


class FFmpegNotFoundError(AudioExtractionError):
    """FFmpeg executable not found."""
    pass


class VideoFileNotFoundError(AudioExtractionError):
    """Video file not found."""
    pass


class AudioExtractionFailedError(AudioExtractionError):
    """Audio extraction failed."""
    pass


# =============================================================================
# Audio Extractor
# =============================================================================

class AudioExtractor:
    """
    Extracts and converts audio from video files using FFmpeg.

    Optimized for ASR with 16kHz mono WAV output.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize audio extractor.

        Args:
            ffmpeg_path: Path to ffmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """
        Check if ffmpeg is available.

        Raises:
            FFmpegNotFoundError: If ffmpeg is not found
        """
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
            )
            logger.info(f"FFmpeg found at {self.ffmpeg_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise FFmpegNotFoundError(
                f"FFmpeg not found at {self.ffmpeg_path}. "
                "Please install FFmpeg: apt-get install ffmpeg"
            )

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
        audio_codec: str = "pcm_s16le",
        audio_track: Optional[int] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Extract audio from video file.

        Args:
            video_path: Path to input video file
            output_path: Path to output audio file
            audio_format: Output format (wav, mp3, etc.)
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of channels (1 for mono)
            audio_codec: Audio codec (pcm_s16le for WAV)
            audio_track: Specific audio track to extract (None for default)
            progress_callback: Optional callback for progress updates

        Returns:
            Path to extracted audio file

        Raises:
            VideoFileNotFoundError: Video file not found
            AudioExtractionFailedError: Extraction failed
        """
        # Check if input is a URL or local file
        is_url = video_path.startswith(("http://", "https://"))
        
        if not is_url:
            video_file = Path(video_path)
            if not video_file.exists():
                raise VideoFileNotFoundError(f"Video file not found: {video_path}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Extracting audio from {video_path} to {output_path} "
            f"(format={audio_format}, sr={sample_rate}Hz, channels={channels})"
        )

        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i", video_path if is_url else str(video_file),
            "-vn",  # No video
            "-acodec", audio_codec,
            "-ar", str(sample_rate),
            "-ac", str(channels),
        ]

        # Select specific audio track if specified
        if audio_track is not None:
            cmd.extend(["-map", f"0:a:{audio_track}"])

        # Overwrite output
        cmd.extend(["-y", str(output_file)])

        try:
            # Get duration for progress tracking (skip for URLs as it may be slow/unreliable)
            duration = None if is_url else self._get_duration(video_path)

            # Run ffmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',  # Ignore encoding errors from media metadata
            )

            # Monitor progress and collect stderr
            stderr_lines = []
            for line in process.stderr:
                stderr_lines.append(line)
                if progress_callback and duration:
                    # Parse time from ffmpeg output
                    # Example: time=00:01:30.45
                    if "time=" in line:
                        try:
                            time_str = line.split("time=")[1].split()[0]
                            current_seconds = self._parse_time(time_str)
                            progress = min(100, (current_seconds / duration) * 100)
                            progress_callback(progress)
                        except (IndexError, ValueError):
                            pass

            process.wait()

            if process.returncode != 0:
                stderr = ''.join(stderr_lines)
                raise AudioExtractionFailedError(
                    f"FFmpeg failed with code {process.returncode}: {stderr}"
                )

            if not output_file.exists():
                raise AudioExtractionFailedError("Output file was not created")

            logger.info(f"Audio extracted successfully to {output_path}")
            return str(output_file)

        except subprocess.SubprocessError as e:
            raise AudioExtractionFailedError(f"FFmpeg execution failed: {e}")

    def extract_audio_segment(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        **kwargs,
    ) -> str:
        """
        Extract a segment of audio from video.

        Args:
            video_path: Path to input video
            output_path: Path to output audio
            start_time: Start time in seconds
            duration: Duration in seconds
            **kwargs: Additional arguments passed to extract_audio

        Returns:
            Path to extracted audio segment
        """
        logger.info(
            f"Extracting audio segment from {video_path} "
            f"(start={start_time}s, duration={duration}s)"
        )

        video_file = Path(video_path)
        if not video_file.exists():
            raise VideoFileNotFoundError(f"Video file not found: {video_path}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command with seek and duration
        cmd = [
            self.ffmpeg_path,
            "-ss", str(start_time),  # Seek to start
            "-i", str(video_file),
            "-t", str(duration),  # Duration
            "-vn",
            "-acodec", kwargs.get("audio_codec", "pcm_s16le"),
            "-ar", str(kwargs.get("sample_rate", 16000)),
            "-ac", str(kwargs.get("channels", 1)),
            "-y", str(output_file),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)

            if not output_file.exists():
                raise AudioExtractionFailedError("Segment file was not created")

            logger.info(f"Audio segment extracted to {output_path}")
            return str(output_file)

        except subprocess.CalledProcessError as e:
            raise AudioExtractionFailedError(
                f"Segment extraction failed: {e.stderr.decode()}"
            )

    def split_audio(
        self,
        video_path: str,
        output_dir: str,
        segment_duration: int = 600,  # 10 minutes
        overlap: int = 10,  # 10 seconds overlap
        **kwargs,
    ) -> list[dict]:
        """
        Split long video into audio segments for ASR processing.

        Args:
            video_path: Path to input video
            output_dir: Directory for output segments
            segment_duration: Duration of each segment in seconds
            overlap: Overlap between segments in seconds
            **kwargs: Additional arguments passed to extract_audio_segment

        Returns:
            List of segment info dicts with 'path', 'start', 'duration'
        """
        logger.info(
            f"Splitting {video_path} into {segment_duration}s segments "
            f"(overlap={overlap}s)"
        )

        # Get total duration
        total_duration = self._get_duration(video_path)
        if not total_duration:
            raise AudioExtractionFailedError("Could not determine video duration")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        segments = []
        current_time = 0
        segment_index = 0

        while current_time < total_duration:
            # Calculate segment duration (handle last segment)
            actual_duration = min(segment_duration, total_duration - current_time)

            # Generate output path
            segment_file = output_path / f"segment_{segment_index:04d}.wav"

            # Extract segment
            self.extract_audio_segment(
                video_path=video_path,
                output_path=str(segment_file),
                start_time=current_time,
                duration=actual_duration,
                **kwargs,
            )

            segments.append({
                "path": str(segment_file),
                "start": current_time,
                "duration": actual_duration,
                "index": segment_index,
            })

            # Move to next segment with overlap
            current_time += segment_duration - overlap
            segment_index += 1

        logger.info(f"Split into {len(segments)} segments")
        return segments

    def _get_duration(self, video_path: str) -> Optional[float]:
        """
        Get video duration using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True,
            )

            duration = float(result.stdout.strip())
            logger.debug(f"Video duration: {duration}s")
            return duration

        except (subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Could not get video duration: {e}")
            return None

    def _parse_time(self, time_str: str) -> float:
        """
        Parse ffmpeg time string to seconds.

        Args:
            time_str: Time string like "00:01:30.45"

        Returns:
            Time in seconds
        """
        parts = time_str.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        return 0.0

    def get_audio_streams(self, video_path: str) -> list[dict]:
        """
        Get information about audio streams in video.

        Args:
            video_path: Path to video file

        Returns:
            List of audio stream info dicts
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index,codec_name,channels,sample_rate,duration",
                "-of", "json",
                str(video_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True,
            )

            import json
            data = json.loads(result.stdout)
            streams = data.get("streams", [])

            logger.info(f"Found {len(streams)} audio streams in {video_path}")
            return streams

        except (subprocess.CalledProcessError, ValueError, KeyError) as e:
            logger.error(f"Failed to get audio streams: {e}")
            return []
