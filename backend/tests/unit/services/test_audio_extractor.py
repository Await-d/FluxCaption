import pytest
from unittest.mock import MagicMock, patch, call


@pytest.mark.unit
class TestAudioExtractor:
    @patch("app.services.audio_extractor.subprocess.run")
    def test_init_sets_ffmpeg_path(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from app.services.audio_extractor import AudioExtractor
        extractor = AudioExtractor()
        assert extractor.ffmpeg_path == "ffmpeg"

    @patch("app.services.audio_extractor.subprocess.run")
    def test_get_audio_streams_subprocess_error_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from app.services.audio_extractor import AudioExtractor
        import subprocess
        extractor = AudioExtractor()
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")
        result = extractor.get_audio_streams("/nonexistent/file.mp4")
        assert result == []

    @patch("app.services.audio_extractor.subprocess.run")
    def test_extract_audio_missing_file_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from app.services.audio_extractor import AudioExtractor, VideoFileNotFoundError
        extractor = AudioExtractor()
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(VideoFileNotFoundError):
                extractor.extract_audio(
                    video_path="/nonexistent/video.mp4",
                    output_path="/tmp/output.wav",
                )
