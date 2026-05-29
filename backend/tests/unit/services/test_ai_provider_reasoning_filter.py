from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_providers.claude_provider import ClaudeProvider
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.ai_providers.ollama_provider import OllamaProvider
from app.services.ai_providers.openai_provider import OpenAIProvider


def _mock_async_client(post_response):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = post_response
    return mock_client


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeStreamClient:
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, *args, **kwargs):
        return _FakeStreamResponse(self._lines)


@pytest.mark.unit
class TestProviderReasoningFilter:
    @pytest.mark.asyncio
    async def test_openai_generate_ignores_reasoning_fields(self):
        provider = OpenAIProvider(api_key="test-key")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "model": "gpt-test",
            "choices": [
                {
                    "message": {
                        "reasoning_content": "hidden reasoning",
                        "content": '{"translation": "visible"}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }

        mock_client = _mock_async_client(response)

        with patch("app.services.ai_providers.openai_provider.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate(model="gpt-test", prompt="hello")

        assert result.text == '{"translation": "visible"}'

    @pytest.mark.asyncio
    async def test_openai_generate_supports_responses_style_output(self):
        provider = OpenAIProvider(api_key="test-key")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "model": "gpt-test",
            "output": [
                {"type": "reasoning", "summary": [{"text": "hidden"}]},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"translation": "visible"}'}],
                },
            ],
            "usage": {"input_tokens": 1, "output_tokens": 2},
        }

        mock_client = _mock_async_client(response)

        with patch("app.services.ai_providers.openai_provider.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate(model="gpt-test", prompt="hello")

        assert result.text == '{"translation": "visible"}'

    @pytest.mark.asyncio
    async def test_openai_stream_skips_reasoning_only_chunks(self):
        provider = OpenAIProvider(api_key="test-key")
        lines = [
            "event: response.reasoning_summary_text.delta",
            'data: {"choices":[{"delta":{"reasoning_content":"hidden"}}]}',
            'data: {"choices":[{"delta":{"content":"{\\"translation\\": \\"visible\\"}"}}]}',
            "data: [DONE]",
        ]

        with patch(
            "app.services.ai_providers.openai_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="gpt-test", prompt="hello")]

        assert chunks == ['{"translation": "visible"}']

    @pytest.mark.asyncio
    async def test_openai_stream_supports_refusal_delta(self):
        provider = OpenAIProvider(api_key="test-key")
        lines = [
            'data: {"type":"response.refusal.delta","delta":"Cannot comply"}',
            "data: [DONE]",
        ]

        with patch(
            "app.services.ai_providers.openai_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="gpt-test", prompt="hello")]

        assert chunks == ["Cannot comply"]

    @pytest.mark.asyncio
    async def test_openai_stream_flushes_trailing_pending_text(self):
        provider = OpenAIProvider(api_key="test-key")
        lines = [
            'data: {"choices":[{"delta":{"content":"visible <"}}]}',
            "data: [DONE]",
        ]

        with patch(
            "app.services.ai_providers.openai_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="gpt-test", prompt="hello")]

        assert chunks == ["visible ", "<"]

    @pytest.mark.asyncio
    async def test_claude_stream_skips_thinking_events(self):
        provider = ClaudeProvider(api_key="test-key")
        lines = [
            'data: {"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"hidden"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"{\\"translation\\": \\"visible\\"}"}}',
        ]

        with patch(
            "app.services.ai_providers.claude_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="claude-test", prompt="hello")]

        assert chunks == ['{"translation": "visible"}']

    @pytest.mark.asyncio
    async def test_claude_stream_flushes_trailing_pending_text(self):
        provider = ClaudeProvider(api_key="test-key")
        lines = [
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"visible <"}}',
        ]

        with patch(
            "app.services.ai_providers.claude_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="claude-test", prompt="hello")]

        assert chunks == ["visible ", "<"]

    @pytest.mark.asyncio
    async def test_gemini_generate_skips_thought_parts(self):
        provider = GeminiProvider(api_key="test-key")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "hidden", "thought": True},
                            {"text": '{"translation": "visible"}'},
                        ]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2},
        }

        mock_client = _mock_async_client(response)

        with patch("app.services.ai_providers.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate(model="gemini-test", prompt="hello")

        assert result.text == '{"translation": "visible"}'
        call_args = mock_client.post.call_args
        assert "test-key" not in call_args.args[0]
        assert call_args.kwargs["headers"]["x-goog-api-key"] == "test-key"

    @pytest.mark.asyncio
    async def test_gemini_generate_handles_empty_candidates(self):
        provider = GeminiProvider(api_key="test-key")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "candidates": [],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 0},
        }

        mock_client = _mock_async_client(response)

        with patch("app.services.ai_providers.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate(model="gemini-test", prompt="hello")

        assert result.text == ""
        assert result.finish_reason is None

    @pytest.mark.asyncio
    async def test_gemini_stream_skips_thought_parts(self):
        provider = GeminiProvider(api_key="test-key")
        lines = [
            '{"candidates":[{"content":{"parts":[{"text":"hidden","thought":true}]}}]}',
            '{"candidates":[{"content":{"parts":[{"text":"{\\"translation\\": \\"visible\\"}"}]}}]}',
        ]

        with patch(
            "app.services.ai_providers.gemini_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="gemini-test", prompt="hello")]

        assert chunks == ['{"translation": "visible"}']

    @pytest.mark.asyncio
    async def test_gemini_stream_flushes_trailing_pending_text(self):
        provider = GeminiProvider(api_key="test-key")
        lines = [
            '{"candidates":[{"content":{"parts":[{"text":"visible <"}]}}]}',
        ]

        with patch(
            "app.services.ai_providers.gemini_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="gemini-test", prompt="hello")]

        assert chunks == ["visible ", "<"]

    @pytest.mark.asyncio
    async def test_ollama_generate_strips_embedded_thinking(self):
        provider = OllamaProvider(base_url="http://ollama.test")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "response": '<think>hidden</think>{"translation": "visible"}',
            "done": True,
        }

        mock_client = _mock_async_client(response)

        with patch("app.services.ai_providers.ollama_provider.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate(model="qwen", prompt="hello")

        assert result.text == '{"translation": "visible"}'

    @pytest.mark.asyncio
    async def test_ollama_stream_supports_message_content_and_embedded_thinking(self):
        provider = OllamaProvider(base_url="http://ollama.test")
        lines = [
            '{"message":{"content":"<think>hidden"}}',
            '{"message":{"content":"</think>{\\"translation\\": \\"visible\\"}"},"done":true}',
        ]

        with patch(
            "app.services.ai_providers.ollama_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="qwen", prompt="hello")]

        assert chunks == ['{"translation": "visible"}']

    @pytest.mark.asyncio
    async def test_ollama_stream_flushes_trailing_pending_text(self):
        provider = OllamaProvider(base_url="http://ollama.test")
        lines = [
            '{"response":"visible <","done":true}',
        ]

        with patch(
            "app.services.ai_providers.ollama_provider.httpx.AsyncClient",
            return_value=_FakeStreamClient(lines),
        ):
            chunks = [chunk async for chunk in provider.generate_stream(model="qwen", prompt="hello")]

        assert chunks == ["visible ", "<"]
