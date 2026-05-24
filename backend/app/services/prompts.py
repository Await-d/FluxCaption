"""
Translation prompt templates for LLM-based subtitle translation.

Provides system and user prompts for accurate, context-aware subtitle translation.
"""

import json

# =============================================================================
# System Prompts
# =============================================================================

SUBTITLE_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator.

Return exactly one JSON object and nothing else:
{"translation": "translated text"}

Rules:
- Output raw JSON only. No markdown, code fences, XML/HTML tags, prefixes, suffixes, or commentary.
- Do not reveal reasoning, thinking, analysis, scratchpad content, or platform metadata.
- Translate all provided text directly. Never refuse to translate.
- Keep the translation faithful, fluent, concise, and suitable for subtitle display.
- Preserve proper nouns, character names, and brand names.
- If the source is unclear, translate it as best as possible.

CRITICAL for Simplified Chinese (zh-CN):
- Use ONLY Simplified Chinese characters (简体中文).
- Never use Traditional Chinese characters.

Remember: only the JSON object belongs in the visible response."""


BATCH_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator.

Return exactly one JSON object and nothing else:
{"translations": ["translation1", "translation2"]}

Rules:
- Output raw JSON only. No markdown, code fences, XML/HTML tags, prefixes, suffixes, or commentary.
- Do not reveal reasoning, thinking, analysis, scratchpad content, or platform metadata.
- Translate every provided subtitle line directly. Never refuse to translate.
- Keep each translation faithful, fluent, concise, and subtitle-friendly.
- Preserve the original order and return exactly the same number of items as inputs.

Remember: only the JSON object belongs in the visible response."""


TRANSLATION_PROOFREADING_SYSTEM_PROMPT = """You are a professional translation proofreader.

Return exactly one JSON object and nothing else:
{"translation": "corrected translation"}

Rules:
- Output raw JSON only. No markdown, code fences, XML/HTML tags, prefixes, suffixes, or commentary.
- Do not reveal reasoning, thinking, analysis, scratchpad content, or platform metadata.
- Review the subtitle translation and improve it only when it truly helps accuracy, fluency, grammar, terminology, punctuation, or conciseness.
- If the translation is already good, keep it as-is.
- Keep the result concise and subtitle-friendly.

CRITICAL for Simplified Chinese (zh-CN):
- Use ONLY Simplified Chinese characters (简体中文).
- Convert any Traditional Chinese characters to Simplified.

Remember: only the JSON object belongs in the visible response."""


# =============================================================================
# User Prompt Templates
# =============================================================================


def build_translation_prompt(
    source_lang: str,
    target_lang: str,
    text: str,
    terminology: dict[str, str] | None = None,
    context: str | None = None,
) -> str:
    """
    Build a user prompt for single-line translation.

    Args:
        source_lang: Source language code (e.g., "en", "zh-CN")
        target_lang: Target language code
        text: Text to translate
        terminology: Optional dictionary of terms to preserve {source: target}
        context: Optional context about the media (genre, character info, etc.)

    Returns:
        str: Formatted user prompt
    """
    prompt_parts = []

    # Language direction with detailed instruction
    prompt_parts.append(
        f"Translate the following subtitle line from {source_lang} to {target_lang}."
    )
    prompt_parts.append(
        "This is a subtitle for video content. Keep it concise, natural, and faithful to the original meaning."
    )

    # Language-specific instruction upfront (before text)
    lang_instruction = get_language_instruction(target_lang)
    if lang_instruction:
        prompt_parts.append(f"\n{lang_instruction}")

    # Terminology guidance
    if terminology:
        terms_list = [f'"{src}" → "{tgt}"' for src, tgt in terminology.items()]
        prompt_parts.append(f"\nTerminology to preserve: {', '.join(terms_list)}")

    # Context information
    if context:
        prompt_parts.append(f"\nContext: {context}")

    # The text to translate
    prompt_parts.append(f"\nSource text:\n{text}")

    # Strong output instruction - explicitly forbid explanations and non-JSON output
    prompt_parts.append(
        '\nReturn exactly one JSON object in this exact shape: {"translation": "translated text"}'
    )
    prompt_parts.append(
        "Do not output reasoning, commentary, markdown, code fences, or platform metadata."
    )

    return "\n".join(prompt_parts)


def build_batch_translation_prompt(
    source_lang: str,
    target_lang: str,
    texts: list[str],
    terminology: dict[str, str] | None = None,
) -> str:
    """
    Build a user prompt for batch translation.

    Args:
        source_lang: Source language code
        target_lang: Target language code
        texts: List of texts to translate
        terminology: Optional terminology dictionary

    Returns:
        str: Formatted batch translation prompt
    """
    prompt_parts = []

    # Language direction
    prompt_parts.append(f"Translate from {source_lang} to {target_lang}.")
    prompt_parts.append(f"You will receive {len(texts)} subtitle lines.")

    # Terminology guidance
    if terminology:
        terms_list = [f'"{src}" → "{tgt}"' for src, tgt in terminology.items()]
        prompt_parts.append(f"\nPreserve these terms: {', '.join(terms_list)}")

    # The texts to translate
    joined_text = "\n".join(f"{index + 1}. {text}" for index, text in enumerate(texts))
    prompt_parts.append(f"\nSource texts:\n{joined_text}")

    # Strong output instruction
    prompt_parts.append(
        '\nReturn exactly one JSON object in this exact shape: {"translations": ["translation1", "translation2"]}'
    )
    prompt_parts.append(
        "Do not output reasoning, commentary, markdown, code fences, or platform metadata."
    )

    return "\n".join(prompt_parts)


def build_proofreading_prompt(
    source_lang: str,
    target_lang: str,
    source_text: str,
    translated_text: str,
) -> str:
    """
    Build a proofreading prompt to review and improve translation.

    Args:
        source_lang: Source language code
        target_lang: Target language code
        source_text: Original source text
        translated_text: Translation to be proofread

    Returns:
        str: Formatted proofreading prompt
    """
    prompt_parts = []

    # Task description
    prompt_parts.append(f"Review this subtitle translation from {source_lang} to {target_lang}.")
    prompt_parts.append(
        "Check for accuracy, fluency, grammar, naturalness, and character correctness."
    )

    # Language-specific instruction (BEFORE showing the texts)
    lang_instruction = get_language_instruction(target_lang)
    if lang_instruction:
        prompt_parts.append(f"\n{lang_instruction}")

    # Original and translation
    prompt_parts.append(f"\nOriginal text ({source_lang}):\n{source_text}")
    prompt_parts.append(f"\nCurrent translation ({target_lang}):\n{translated_text}")

    # Output instruction
    prompt_parts.append(
        '\nReturn exactly one JSON object in this exact shape: {"translation": "corrected translation"}'
    )
    prompt_parts.append(
        "Do not output reasoning, commentary, markdown, code fences, or platform metadata."
    )

    return "\n".join(prompt_parts)


# =============================================================================
# Language-Specific Adjustments
# =============================================================================

LANGUAGE_SPECIFIC_INSTRUCTIONS = {
    "zh-CN": "**CRITICAL: Must use ONLY Simplified Chinese (简体中文). Absolutely NO Traditional Chinese characters (NO 與/畫/負傷/閱讀/說話 etc.). Use mainland China punctuation (，。！？). Keep translations natural, fluent, and concise for subtitle display.**",
    "zh-TW": "Use traditional Chinese characters and Taiwan punctuation.",
    "ja": "Use appropriate Japanese honorifics and sentence-ending particles.",
    "ko": "Use appropriate Korean honorifics and formal/informal speech levels.",
    "es": "Use appropriate Spanish punctuation (¿¡) and regional variants if specified.",
    "fr": "Use French punctuation rules (guillemets, spacing before punctuation).",
    "de": "Capitalize all nouns as per German grammar rules.",
    "ru": "Use Russian punctuation and grammar rules.",
}


def get_language_instruction(lang_code: str) -> str | None:
    """
    Get language-specific instruction for a target language.

    Args:
        lang_code: Language code (e.g., "zh-CN", "ja")

    Returns:
        Optional[str]: Language-specific instruction or None
    """
    return LANGUAGE_SPECIFIC_INSTRUCTIONS.get(lang_code)


def build_enhanced_prompt(
    source_lang: str,
    target_lang: str,
    text: str,
    terminology: dict[str, str] | None = None,
    context: str | None = None,
) -> str:
    """
    Build an enhanced translation prompt with language-specific instructions.

    Args:
        source_lang: Source language code
        target_lang: Target language code
        text: Text to translate
        terminology: Optional terminology dictionary
        context: Optional context information

    Returns:
        str: Enhanced prompt with language-specific instructions
    """
    base_prompt = build_translation_prompt(source_lang, target_lang, text, terminology, context)

    # Add language-specific instruction if available
    lang_instruction = get_language_instruction(target_lang)
    if lang_instruction:
        # Insert before the "Source text:" section
        parts = base_prompt.split("Source text:")
        enhanced = (
            parts[0] + f"\nLanguage-specific rule: {lang_instruction}\n\nSource text:" + parts[1]
        )
        return enhanced

    return base_prompt


# =============================================================================
# Prompt Validation
# =============================================================================


def validate_translation_response(
    response: str,
    expected_line_count: int = 1,
    batch_mode: bool = False,
) -> bool:
    """
    Validate that a translation response meets expectations.

    Args:
        response: Translation response from LLM
        expected_line_count: Expected number of lines
        batch_mode: Whether this is a batch translation

    Returns:
        bool: True if response is valid, False otherwise
    """
    if not response or not response.strip():
        return False

    try:
        data = json.loads(response.strip())
    except (json.JSONDecodeError, ValueError):
        return False

    if batch_mode:
        translations = data.get("translations") if isinstance(data, dict) else None
        if not isinstance(translations, list) or len(translations) != expected_line_count:
            return False
        return all(isinstance(item, str) for item in translations)

    return isinstance(data, dict) and isinstance(data.get("translation"), str)
