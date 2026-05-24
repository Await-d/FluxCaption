import json

import pytest

from app.services.ai_response_cleaner import (
    ReasoningBlockFilter,
    extract_visible_text,
    extract_visible_text_from_json_line,
    strip_reasoning_blocks,
)


@pytest.mark.unit
class TestStripReasoningBlocks:
    def test_strips_complete_reasoning_blocks(self):
        response = '<think>hidden</think>{"translation": "visible"}'

        assert strip_reasoning_blocks(response) == '{"translation": "visible"}'

    def test_strips_dangling_reasoning_block(self):
        response = 'visible<thinking>hidden without close'

        assert strip_reasoning_blocks(response) == 'visible'

    def test_strips_nested_reasoning_blocks(self):
        response = 'visible<think>a<think>b</think>c</think> done'

        assert strip_reasoning_blocks(response) == 'visible done'


@pytest.mark.unit
class TestReasoningBlockFilter:
    def test_filters_reasoning_across_chunks(self):
        reasoning_filter = ReasoningBlockFilter()

        chunks = [
            'hello <thi',
            'nk>hidden',
            '</think> world',
        ]

        assert ''.join(reasoning_filter.filter(chunk) for chunk in chunks) == 'hello  world'

    def test_keeps_non_reasoning_tags(self):
        reasoning_filter = ReasoningBlockFilter()

        assert reasoning_filter.filter('<b>visible</b>') == '<b>visible</b>'

    def test_flush_keeps_plain_unclosed_angle_text(self):
        reasoning_filter = ReasoningBlockFilter()

        assert reasoning_filter.filter('visible < 3') + reasoning_filter.flush() == 'visible < 3'

    def test_flush_keeps_plain_unclosed_angle(self):
        reasoning_filter = ReasoningBlockFilter()

        assert reasoning_filter.filter('visible <') + reasoning_filter.flush() == 'visible <'

    def test_flush_drops_partial_reasoning_tag(self):
        reasoning_filter = ReasoningBlockFilter()

        assert reasoning_filter.filter('visible <thi') + reasoning_filter.flush() == 'visible '

    def test_flush_drops_partial_closing_reasoning_tag(self):
        reasoning_filter = ReasoningBlockFilter()

        assert reasoning_filter.filter('visible </thi') + reasoning_filter.flush() == 'visible '


@pytest.mark.unit
class TestExtractVisibleText:
    def test_openai_responses_output_text(self):
        payload = {
            "output": [
                {"type": "reasoning", "summary": [{"text": "hidden"}]},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"translation": "visible"}'}],
                },
            ]
        }

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_openai_reasoning_only_returns_empty(self):
        payload = {
            "choices": [
                {
                    "delta": {
                        "reasoning_content": "hidden",
                    }
                }
            ]
        }

        assert extract_visible_text(payload) == ""

    def test_openai_legacy_completion_text(self):
        payload = {"choices": [{"text": '{"translation": "visible"}'}]}

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_openai_choices_skip_reasoning_only_choice(self):
        payload = {
            "choices": [
                {"delta": {"reasoning_content": "hidden"}},
                {"delta": {"content": '{"translation": "visible"}'}},
            ]
        }

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_openai_refusal_is_visible_fallback(self):
        payload = {"choices": [{"message": {"refusal": "Cannot comply"}}]}

        assert extract_visible_text(payload) == "Cannot comply"

    def test_openai_chat_delta_refusal_is_visible_fallback(self):
        payload = {"choices": [{"delta": {"refusal": "Cannot comply"}}]}

        assert extract_visible_text(payload) == "Cannot comply"

    def test_openai_reasoning_summary_delta_returns_empty(self):
        payload = {"type": "response.reasoning_summary_text.delta", "delta": "hidden"}

        assert extract_visible_text(payload) == ""

    def test_openai_output_item_done_extracts_item_content(self):
        payload = {
            "type": "response.output_item.done",
            "item": {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"translation": "visible"}'}],
            },
        }

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_openai_response_completed_extracts_response_output(self):
        payload = {
            "type": "response.completed",
            "response": {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"translation": "visible"}'}],
                    }
                ]
            },
        }

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_openai_tool_call_delta_returns_empty(self):
        payload = {"type": "response.function_call_arguments.delta", "delta": "hidden"}

        assert extract_visible_text(payload) == ""

    def test_deeply_nested_payload_returns_empty(self):
        payload = "visible"
        for _ in range(70):
            payload = [payload]

        assert extract_visible_text(payload) == ""

    def test_claude_thinking_blocks_are_skipped(self):
        payload = [
            {"type": "thinking", "thinking": "hidden"},
            {"type": "text", "text": '{"translation": "visible"}'},
        ]

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_gemini_thought_signature_only_returns_empty(self):
        payload = {"candidates": [{"content": {"parts": [{"thoughtSignature": "abc"}]}}]}

        assert extract_visible_text(payload) == ""

    def test_gemini_candidates_skip_thought_only_candidate(self):
        payload = {
            "candidates": [
                {"content": {"parts": [{"thoughtSignature": "abc"}]}},
                {"content": {"parts": [{"text": '{"translation": "visible"}'}]}},
            ]
        }

        assert extract_visible_text(payload) == '{"translation": "visible"}'

    def test_json_line_extracts_visible_text(self):
        line = json.dumps({"type": "response.output_text.delta", "delta": "hello"})

        assert extract_visible_text_from_json_line(line) == "hello"

    def test_non_json_stream_line_returns_empty(self):
        assert extract_visible_text_from_json_line("event: response.output_text.delta") == ""
