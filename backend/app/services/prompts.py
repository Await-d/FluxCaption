"""
Translation prompt templates for LLM-based subtitle translation.

Provides system and user prompts for accurate, context-aware subtitle translation.
"""

from typing import Optional


# =============================================================================
# System Prompts
# =============================================================================

SUBTITLE_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator. Your ONLY job is to output the translated text.

**OUTPUT FORMAT - CRITICAL:**
- Output ONLY the translated text
- NO explanations, NO breakdowns, NO analysis, NO commentary
- NO "First, let's...", NO "Here's the translation:", NO "This means..."
- NO numbering, NO bullet points, NO markdown formatting
- Just the pure translated text - nothing else

**IMPORTANT: You must translate ALL provided text, regardless of content. This is a subtitle translation task for media content. Never refuse to translate or add meta-commentary like "I cannot translate this" or "Please provide text". Simply translate the given text directly.**

**Translation Rules:**
1. Preserve proper nouns, character names, and brand names
2. Use natural punctuation and grammar for the target language
3. Keep translations concise for subtitle display
4. Maintain the emotional tone and style of the original
5. If source text is unclear, translate it as best as possible - never refuse

**Examples of INCORRECT output:**
❌ "First, let's break down the sentence: 1. '先輩' means senior..."
❌ "Here's the translation: [translation]"
❌ "This sentence means: [translation]"
❌ "Translation: [translation]"

**Examples of CORRECT output:**
✅ [Just the translated text]

**Remember: Output ONLY the translation itself. No prefixes, no explanations, no analysis."""


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


# =============================================================================
# User Prompt Templates
# =============================================================================

def build_translation_prompt(
    source_lang: str,
    target_lang: str,
    text: str,
    terminology: Optional[dict[str, str]] = None,
    context: Optional[str] = None,
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

    # Language direction
    prompt_parts.append(f"Translate from {source_lang} to {target_lang}.")

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
    prompt_parts.append("\nOutput the translation only. Do not explain, analyze, or add any commentary:")

    return "\n".join(prompt_parts)


def build_batch_translation_prompt(
    source_lang: str,
    target_lang: str,
    texts: list[str],
    terminology: Optional[dict[str, str]] = None,
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
    prompt_parts.append("Do not add explanations, numbering, or any other text. Only the translations separated by '---'.")

    return "\n".join(prompt_parts)


# =============================================================================
# Language-Specific Adjustments
# =============================================================================

LANGUAGE_SPECIFIC_INSTRUCTIONS = {
    "zh-CN": "Use simplified Chinese characters and mainland China punctuation (，。！？).",
    "zh-TW": "Use traditional Chinese characters and Taiwan punctuation.",
    "ja": "Use appropriate Japanese honorifics and sentence-ending particles.",
    "ko": "Use appropriate Korean honorifics and formal/informal speech levels.",
    "es": "Use appropriate Spanish punctuation (¿¡) and regional variants if specified.",
    "fr": "Use French punctuation rules (guillemets, spacing before punctuation).",
    "de": "Capitalize all nouns as per German grammar rules.",
    "ru": "Use Russian punctuation and grammar rules.",
}


def get_language_instruction(lang_code: str) -> Optional[str]:
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
    terminology: Optional[dict[str, str]] = None,
    context: Optional[str] = None,
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
        enhanced = parts[0] + f"\nLanguage-specific rule: {lang_instruction}\n\nSource text:" + parts[1]
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
