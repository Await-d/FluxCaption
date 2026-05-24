"""Utilities for removing visible AI reasoning from provider responses."""

import json

REASONING_TAG_NAMES = ("think", "thinking", "reasoning", "analysis")
REASONING_BLOCK_TYPES = {
    "reasoning",
    "reasoning_delta",
    "reasoning_summary",
    "reasoning_summary_text",
    "redacted_thinking",
    "signature_delta",
    "thinking",
    "thinking_delta",
}
VISIBLE_TEXT_KEYS = ("content", "text", "output_text", "response", "refusal", "output")
MAX_VISIBLE_TEXT_DEPTH = 64


def strip_reasoning_blocks(text: str) -> str:
    """Remove visible reasoning blocks from a complete model response."""
    reasoning_filter = ReasoningBlockFilter()
    return (reasoning_filter.filter(text) + reasoning_filter.flush()).strip()


def extract_visible_text(value, _depth: int = 0) -> str:
    """Extract visible text from a provider payload or raw string."""
    if _depth > MAX_VISIBLE_TEXT_DEPTH:
        return ""

    if value is None:
        return ""

    if isinstance(value, str):
        return strip_reasoning_blocks(value)

    if isinstance(value, list):
        parts = [extract_visible_text(item, _depth + 1) for item in value]
        return strip_reasoning_blocks("".join(parts))

    if isinstance(value, dict):
        value_type = value.get("type")
        if value.get("thought") is True:
            return ""
        if isinstance(value_type, str) and _is_reasoning_type(value_type):
            return ""

        event_visible_text = _extract_visible_event_text(value, _depth)
        if event_visible_text:
            return event_visible_text

        if "message" in value and isinstance(value["message"], dict):
            visible = extract_visible_text(
                value["message"].get("content") or value["message"].get("refusal"),
                _depth + 1,
            )
            if visible:
                return visible

        if "choices" in value and isinstance(value["choices"], list) and value["choices"]:
            return _extract_first_visible(value["choices"], _depth)

        if "candidates" in value and isinstance(value["candidates"], list) and value["candidates"]:
            return _extract_first_visible(value["candidates"], _depth)

        if "output" in value and isinstance(value["output"], list):
            return extract_visible_text(value["output"], _depth + 1)

        if "content_block" in value and isinstance(value["content_block"], dict):
            return extract_visible_text(value["content_block"], _depth + 1)

        if "delta" in value and isinstance(value["delta"], dict):
            delta = value["delta"]
            delta_type = delta.get("type")
            if isinstance(delta_type, str) and _is_reasoning_type(delta_type):
                return ""
            visible = extract_visible_text(
                delta.get("content")
                or delta.get("text")
                or delta.get("output_text")
                or delta.get("refusal"),
                _depth + 1,
            )
            if visible:
                return visible

        if "parts" in value and isinstance(value["parts"], list):
            visible_parts = []
            for part in value["parts"]:
                if not isinstance(part, dict):
                    continue
                if part.get("thought") is True:
                    continue
                part_type = part.get("type")
                if isinstance(part_type, str) and _is_reasoning_type(part_type):
                    continue
                if part.get("thoughtSignature") and not part.get("text") and not part.get("content"):
                    continue
                visible = extract_visible_text(part.get("text") or part.get("content"), _depth + 1)
                if visible:
                    visible_parts.append(visible)
            return strip_reasoning_blocks("".join(visible_parts))

        for key in VISIBLE_TEXT_KEYS:
            if key in value and value[key] is not None:
                visible = extract_visible_text(value[key], _depth + 1)
                if visible:
                    return visible

        return ""

    return strip_reasoning_blocks(str(value))


def _is_reasoning_type(value_type: str) -> bool:
    lowered = value_type.lower()
    return any(reasoning_type in lowered for reasoning_type in REASONING_BLOCK_TYPES)


def _extract_first_visible(items: list, _depth: int) -> str:
    for item in items:
        visible = extract_visible_text(item, _depth + 1)
        if visible:
            return visible
    return ""


def _extract_visible_event_text(value: dict, _depth: int) -> str:
    value_type = value.get("type")
    if not isinstance(value_type, str):
        return ""

    lowered_type = value_type.lower()
    if _is_reasoning_type(lowered_type):
        return ""

    if lowered_type in {
        "response.refusal.delta",
        "response.refusal.done",
        "response.content_part.done",
        "response.output_text.delta",
        "response.output_text.done",
        "response.output_item.done",
        "response.text.delta",
        "response.text.done",
        "content_block_delta",
    }:
        return extract_visible_text(
            value.get("delta")
            or value.get("text")
            or value.get("content")
            or value.get("item")
            or value.get("part"),
            _depth + 1,
        )

    if lowered_type in {
        "response.output_item.added",
        "response.content_part.added",
        "content_block_start",
    }:
        return extract_visible_text(
            value.get("item") or value.get("part") or value.get("content_block"),
            _depth + 1,
        )

    return ""


class ReasoningBlockFilter:
    """Stateful filter for streaming chunks that may contain split reasoning tags."""

    def __init__(self) -> None:
        self._reasoning_depth = 0
        self._pending = ""

    def filter(self, chunk: str) -> str:
        """Return the visible part of a stream chunk."""
        if not chunk:
            return ""

        text = self._pending + chunk
        self._pending = ""
        output = []
        index = 0

        while index < len(text):
            char = text[index]
            if char != "<":
                if self._reasoning_depth == 0:
                    output.append(char)
                index += 1
                continue

            tag_end = text.find(">", index)
            if tag_end == -1:
                self._pending = text[index:]
                break

            raw_tag = text[index + 1 : tag_end].strip().lower()
            is_closing_tag = raw_tag.startswith("/")
            tag_name = raw_tag[1:].split()[0] if is_closing_tag else raw_tag.split()[0]
            tag_name = tag_name.rstrip("/")

            if tag_name in REASONING_TAG_NAMES:
                if is_closing_tag:
                    self._reasoning_depth = max(0, self._reasoning_depth - 1)
                elif not raw_tag.endswith("/"):
                    self._reasoning_depth += 1
                index = tag_end + 1
                continue

            if self._reasoning_depth == 0:
                output.append(text[index : tag_end + 1])
            index = tag_end + 1

        return "".join(output)

    def flush(self) -> str:
        """Return any pending non-reasoning text at the end of a complete response."""
        if not self._pending:
            return ""

        pending = self._pending
        self._pending = ""
        if self._reasoning_depth > 0 or _is_partial_reasoning_tag(pending):
            return ""

        return pending


def _is_partial_reasoning_tag(text: str) -> bool:
    candidate = text.lower().lstrip("<").lstrip("/")
    if not candidate:
        return False
    return any(tag.startswith(candidate) for tag in REASONING_TAG_NAMES)


def extract_visible_text_from_json_line(line: str) -> str:
    """Extract visible text from a JSON line, if the line is JSON encoded."""
    stripped = line.strip()
    if not stripped:
        return ""

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""

    return extract_visible_text(parsed)
