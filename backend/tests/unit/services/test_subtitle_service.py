from unittest.mock import MagicMock, patch

import pytest

from app.services.subtitle_service import (
    DIRECT_TRANSLATION_PROVIDERS,
    apply_correction_rules,
    extract_translation_from_response,
    strip_ass_tags,
)


@pytest.mark.unit
class TestExtractTranslationFromResponse:
    def test_direct_json(self):
        resp = '{"translation": "\u4f60\u597d\u4e16\u754c"}'
        assert extract_translation_from_response(resp) == "\u4f60\u597d\u4e16\u754c"

    def test_json_with_thinking_block(self):
        resp = '<think>reasoning hidden</think>{"translation": "\u4f60\u597d\u4e16\u754c"}'
        assert extract_translation_from_response(resp) == "\u4f60\u597d\u4e16\u754c"

    def test_fenced_json_with_reasoning(self):
        resp = '```json\n<thinking>step</thinking>{"translation": "\u4f60\u597d\u4e16\u754c"}\n```'
        assert extract_translation_from_response(resp) == "\u4f60\u597d\u4e16\u754c"

    def test_plain_text_fallback(self):
        resp = "\u4f60\u597d\u4e16\u754c"
        assert extract_translation_from_response(resp) == "\u4f60\u597d\u4e16\u754c"

    def test_empty_string(self):
        assert extract_translation_from_response("") == ""

    def test_none_returns_empty(self):
        assert extract_translation_from_response(None) == ""


@pytest.mark.unit
class TestStripAssTags:
    def test_plain_text_unchanged(self):
        text = "Hello world"
        plain, tags = strip_ass_tags(text)
        assert plain == "Hello world"
        assert tags == []

    def test_empty_string(self):
        plain, tags = strip_ass_tags("")
        assert plain == ""
        assert tags == []


@pytest.mark.unit
class TestApplyCorrectionRules:
    def test_no_session_returns_original(self):
        result = apply_correction_rules("hello", "en", "zh-CN", db_session=None)
        assert result == "hello"

    def test_empty_text(self):
        result = apply_correction_rules("", "en", "zh-CN", db_session=None)
        assert result == ""


@pytest.mark.unit
class TestDirectTranslationProviders:
    def test_deeplx_uses_direct_translation_path(self):
        assert "deeplx" in DIRECT_TRANSLATION_PROVIDERS
