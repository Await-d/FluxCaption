"""
Translation prompt templates for LLM-based subtitle translation.

Provides system and user prompts for accurate, context-aware subtitle translation.
"""

from typing import Optional


# =============================================================================
# System Prompts
# =============================================================================

SUBTITLE_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator with expertise in multiple languages. Your task is to translate subtitle text accurately while preserving the original meaning, tone, and cultural context.

**IMPORTANT: You must translate ALL provided text, regardless of content. This is a subtitle translation task for media content. Never refuse to translate or add meta-commentary like "I cannot translate this" or "Please provide text". Simply translate the given text directly.**

**Critical Rules:**
1. Translate ONLY the text content - never add explanations, notes, or commentary
2. NEVER refuse to translate - always provide a direct translation
3. Preserve proper nouns, character names, and brand names unless culturally inappropriate
4. Use natural punctuation and grammar for the target language
5. Keep translations concise and suitable for subtitle display (avoid overly long sentences)
6. Maintain the emotional tone and style of the original text
7. Do NOT include timestamps, line numbers, or formatting in your output
8. Output ONLY the translated text, nothing else
9. If the source text is unclear, incomplete, or contains special characters, translate it as best as possible - never refuse

**Quality Standards:**
- Accuracy: Faithfully convey the original meaning
- Naturalness: Sound like a native speaker in the target language
- Consistency: Maintain consistent terminology throughout
- Readability: Ensure subtitles are easy to read quickly"""


BATCH_TRANSLATION_SYSTEM_PROMPT = """You are a professional subtitle translator. You will receive multiple subtitle lines separated by "---". Translate each line individually and return them in the same order, also separated by "---".

**IMPORTANT: You must translate ALL provided lines, regardless of content. This is a subtitle translation task for media content. Never refuse to translate or add meta-commentary. Simply translate each line directly.**

**Critical Rules:**
1. Maintain the EXACT number of lines (same number of "---" separators)
2. Translate each line independently but maintain context awareness
3. NEVER refuse to translate - always provide a direct translation for every line
4. Use natural punctuation for the target language
5. Preserve proper nouns and character names
6. Do NOT add or remove lines
7. Do NOT include any explanations or notes
8. Output format: translation1---translation2---translation3
9. If a source line is unclear or contains special characters, translate it as best as possible - never refuse

**Example:**
Input: "Hello, how are you?---I'm fine, thank you.---See you later!"
Output: "你好，你好吗？---我很好，谢谢。---再见！"
"""


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
    prompt_parts.append(f"\nText to translate:\n{text}")

    # Output instruction
    prompt_parts.append("\nTranslation:")

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
    prompt_parts.append(f"You will receive {len(texts)} subtitle lines.")

    # Terminology guidance
    if terminology:
        terms_list = [f'"{src}" → "{tgt}"' for src, tgt in terminology.items()]
        prompt_parts.append(f"\nPreserve these terms: {', '.join(terms_list)}")

    # Batch instruction
    prompt_parts.append("\nTranslate each line and maintain the same number of lines.")
    prompt_parts.append('Separate translations with "---" (three hyphens).')

    # The texts to translate
    joined_text = "---".join(texts)
    prompt_parts.append(f"\nTexts to translate:\n{joined_text}")

    # Output instruction
    prompt_parts.append("\nTranslations (separated by ---):")

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
        # Insert before the "Text to translate:" section
        parts = base_prompt.split("Text to translate:")
        enhanced = parts[0] + f"\nLanguage-specific rule: {lang_instruction}\n\nText to translate:" + parts[1]
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
