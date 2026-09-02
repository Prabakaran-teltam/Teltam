import os
import time
import logging
from openai import RateLimitError, APIConnectionError, APIStatusError, APITimeoutError
from django.conf import settings
from app.services.openai_document_service import get_openai_client
from app.constants import LANGUAGES

logger = logging.getLogger(__name__)

def get_language_name(code):
    if code == 'auto':
        return 'Auto-Detect'
    for lang in LANGUAGES:
        if lang['code'] == code:
            return lang['name']
    return code

def translate_text_with_openai_semantic(text, target_lang, source_lang="auto"):
    """
    Translates text semantically using OpenAI gpt-4o-mini following the custom rules.
    Optimized for low latency (shortened prompt) and exact deterministic output (temp=0.0).
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API client is not configured. Please set OPENAI_API_KEY.")
        
    if not text or not text.strip():
        return ""

    source_name = get_language_name(source_lang)
    target_name = get_language_name(target_lang)

    # Highly condensed prompt to minimize token input latency while keeping all translation rules
    system_prompt = (
        "You are an expert multilingual AI translator performing semantic translation.\n"
        "Rules:\n"
        "1. Translate the meaning naturally into the target language. Do not transliterate or mix languages.\n"
        "2. Return ONLY the translated text. Do not include pronunciation, notes, explanations, quotes, or language names.\n"
        "3. Preserve the tone, correct spelling/grammar mistakes, and translate slang naturally.\n"
        "4. If source and target languages are identical, return the text with corrected spelling and grammar only (no translation).\n"
        "Always translate by meaning, never by pronunciation."
    )

    user_prompt = (
        f"Source: {source_name}\n"
        f"Target: {target_name}\n"
        f"Text:\n{text}"
    )

    max_retries = 3
    backoff = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,  # 0.0 forces exact deterministic translation
                timeout=45
            )
            return response.choices[0].message.content.strip()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI rate limit in text translation. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)
        except (APITimeoutError, APIConnectionError, APIStatusError) as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI API issue ({type(e).__name__}: {str(e)}) in text translation. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)


def generate_transliteration_with_openai(translated_text, target_lang="auto"):
    """
    Generates a phonetic transliteration (pronunciation reading in Latin/English script)
    for the translated text using OpenAI gpt-4o-mini API.
    """
    client = get_openai_client()
    if not client or not translated_text or not translated_text.strip():
        return ""

    target_name = get_language_name(target_lang)

    # Truncate text for transliteration to prevent API timeout on long documents
    sample_text = translated_text.strip()
    if len(sample_text) > 1500:
        sample_text = sample_text[:1500] + "..."

    system_prompt = (
        "You are an expert linguistic transliterator.\n"
        "Your task is to convert the given text into a phonetic transliteration (pronunciation guide in standard Latin/English alphabet).\n"
        "Rules:\n"
        "1. Write out the exact phonetic pronunciation using readable English/Latin letters.\n"
        "2. If the text is already written in English or Latin script, return the text cleanly with phonetic reading accents if helpful, or return the text itself.\n"
        "3. Return ONLY the transliterated phonetic text. Do not add quotes, notes, explanations, or language labels."
    )

    user_prompt = f"Target Language: {target_name}\nText:\n{sample_text}"

    max_retries = 3
    backoff = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                timeout=45
            )
            return response.choices[0].message.content.strip()
        except (APITimeoutError, APIConnectionError, APIStatusError, RateLimitError) as e:
            logger.warning(f"OpenAI transliteration issue ({type(e).__name__}: {str(e)}), attempt {attempt+1}/{max_retries}...")
            if attempt == max_retries - 1:
                return ""
            time.sleep(backoff ** attempt)
        except Exception as e:
            logger.warning(f"Unexpected OpenAI transliteration error: {str(e)}")
            return ""
    return ""
