import pytest
from unittest.mock import MagicMock, patch

from app.services.asr_factory import ASRFactory, ASREngine


@pytest.mark.unit
class TestASRFactory:
    def test_unknown_engine_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown ASR engine"):
            ASRFactory.create_asr_service(engine="unknown_engine")

    def test_faster_whisper_engine_name(self):
        assert ASREngine.FASTER_WHISPER == "faster-whisper"

    def test_funasr_engine_name(self):
        assert ASREngine.FUNASR == "funasr"

    def test_get_available_engines_returns_list(self):
        engines = ASRFactory.get_available_engines()
        assert isinstance(engines, list)

    def test_validate_engine_unknown_returns_false(self):
        assert ASRFactory.validate_engine("nonexistent_engine") is False

    @patch("app.services.asr_factory.settings")
    def test_default_engine_from_settings(self, mock_settings):
        mock_settings.asr_engine = "faster-whisper"
        with patch("app.services.asr_factory.ASRFactory.create_asr_service") as mock_create:
            mock_create.return_value = MagicMock()
            ASRFactory.get_default_asr_service()
            mock_create.assert_called_once()
