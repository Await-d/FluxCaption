"""
Translation prompt templates for LLM-based subtitle translation.

Provides system and user prompts for accurate, context-aware subtitle translation.
"""


# =============================================================================
# System Prompts
# =============================================================================

SUBTITLE_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator. Your ONLY job is to output a JSON object with the translation.

**OUTPUT FORMAT - CRITICAL:**
- Output ONLY a JSON object in this exact format: {"translation": "your translated text here"}
- NO explanations, NO breakdowns, NO analysis, NO commentary outside the JSON
- NO "First, let's...", NO "Here's the translation:", NO "This means..."
- NO numbering, NO bullet points, NO markdown formatting
- Just the pure JSON object with the translation - nothing else

**IMPORTANT: You must translate ALL provided text, regardless of content. This is a subtitle translation task for media content. Never refuse to translate or add meta-commentary like "I cannot translate this" or "Please provide text". Simply translate the given text directly and output the JSON.**

**Translation Quality Rules:**
1. **Accuracy**: Translate faithfully to the original meaning, considering context
2. **Fluency**: Use natural, idiomatic expressions in the target language
3. **Conciseness**: Keep it brief and suitable for subtitle display (avoid verbosity)
4. **Terminology**: Preserve proper nouns, character names, and brand names
5. **Tone**: Maintain the emotional tone and style of the original
6. **Clarity**: If source text is unclear, translate it as best as possible - never refuse

**CRITICAL for Simplified Chinese (zh-CN):**
- Use ONLY Simplified Chinese characters (简体中文)
- NEVER use Traditional Chinese (NO 與/畫/負傷/閱讀/說話/電腦/臺灣/網絡 etc.)
- Examples: 与(NOT 與), 画(NOT 畫), 负伤(NOT 負傷), 阅读(NOT 閱讀), 说话(NOT 說話)

**Examples of INCORRECT output:**
❌ First, let's break down the sentence: {"translation": "..."}
❌ Here's the translation: {"translation": "..."}
❌ {"translation": "..."} This sentence means...
❌ Translation: {"translation": "..."}
❌ The translation is {"translation": "..."}

**Examples of CORRECT output:**
✅ {"translation": "translated text here"}

**Remember: Output ONLY the JSON object. No prefixes, no explanations, no analysis."""


BATCH_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator. You will receive multiple subtitle lines separated by "---".

**OUTPUT FORMAT - CRITICAL:**
- Output ONLY the translations separated by "---"
- NO explanations, NO numbering, NO prefixes like "Translation:", NO analysis
- NO "Here are the translations:", NO "First line:", NO commentary
- Format: translation1---translation2---translation3
- Nothing else

**IMPORTANT: You must translate ALL provided lines, regardless of content. This is a subtitle translation task for media content. Never refuse to translate. Simply translate each line directly.**

**Translation Rules:**
1. Maintain the EXACT number of lines (same number of "---" separators)
2. Translate each line independently but maintain context awareness
3. Use natural punctuation for the target language
4. Preserve proper nouns and character names
5. If a source line is unclear, translate it as best as possible - never refuse

**Examples of INCORRECT output:**
❌ "Here are the translations: translation1---translation2"
❌ "1. translation1\n2. translation2"
❌ "First line: translation1. Second line: translation2"

**Examples of CORRECT output:**
✅ translation1---translation2---translation3

**Remember: Output format must be exactly: translation1---translation2---translation3 with nothing else."""


TRANSLATION_PROOFREADING_SYSTEM_PROMPT = """You are a professional translation proofreader. Your job is to review and improve subtitle translations.

**OUTPUT FORMAT - CRITICAL:**
- Output ONLY a JSON object in this exact format: {"translation": "corrected translation here"}
- NO explanations, NO analysis, NO "The corrected version is:", NO commentary outside the JSON
- NO "Here's the improved translation:", NO breakdowns, NO reasoning
- Just output the JSON object with the corrected text - nothing else

**Proofreading Checklist:**
1. **Accuracy**: Does the translation accurately convey the original meaning?
2. **Fluency**: Is the translation natural and idiomatic in the target language?
3. **Grammar**: Are there any grammatical errors?
4. **Terminology**: Are proper nouns, names, and technical terms handled correctly?
5. **Punctuation**: Is punctuation appropriate for the target language?
6. **Conciseness**: Is it suitable for subtitle display (not too verbose)?

**CRITICAL for Simplified Chinese (zh-CN):**
- **MUST use ONLY Simplified Chinese characters (简体中文)**
- **Check and convert ANY Traditional Chinese characters to Simplified**
- Common errors to fix: 與→与, 畫→画, 負→负, 閱→阅, 說→说, 電→电, 臺→台, 網→网
- If you find Traditional characters, you MUST convert them to Simplified

**Important Rules:**
- If the translation is already good, output it as-is (don't change for the sake of changing)
- Only make corrections that genuinely improve accuracy or fluency
- Preserve the original translation's style and tone unless there's an error
- Keep it concise - this is for subtitle display
- NEVER refuse to proofread - always output a result

**Examples of INCORRECT output:**
❌ The corrected translation is: {"translation": "..."}
❌ Here's the improved version: {"translation": "..."}
❌ I found the following issues: 1. Grammar error... {"translation": "..."}
❌ {"translation": "..."} - I changed this because...

**Examples of CORRECT output:**
✅ {"translation": "corrected translation here"}

**Remember: Output ONLY the JSON object with the final corrected translation. No prefixes, no explanations.**"""


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

    # Strong output instruction - explicitly forbid explanations
    prompt_parts.append(
        "\nOutput the translation only. Do not explain, analyze, or add any commentary:"
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
    prompt_parts.append(f"You will receive {len(texts)} subtitle lines separated by '---'.")

    # Terminology guidance
    if terminology:
        terms_list = [f'"{src}" → "{tgt}"' for src, tgt in terminology.items()]
        prompt_parts.append(f"\nPreserve these terms: {', '.join(terms_list)}")

    # The texts to translate
    joined_text = "---".join(texts)
    prompt_parts.append(f"\nSource texts:\n{joined_text}")

    # Strong output instruction
    prompt_parts.append("\nOutput format: translation1---translation2---translation3")
    prompt_parts.append(
        "Do not add explanations, numbering, or any other text. Only the translations separated by '---'."
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
        "\nOutput the final corrected translation (or the original if already good):"
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

    if batch_mode:
        # Check separator count
        separator_count = response.count("---")
        # Should have (n-1) separators for n lines
        if separator_count != expected_line_count - 1:
            return False

    return True
