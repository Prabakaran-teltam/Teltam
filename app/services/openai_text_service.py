import os
import time
import logging
from openai import RateLimitError, APIConnectionError, APIStatusError
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
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API client is not configured. Please set OPENAI_API_KEY.")
        
    if not text or not text.strip():
        return ""

    source_name = get_language_name(source_lang)
    target_name = get_language_name(target_lang)

    system_prompt = (
        "You are an expert multilingual AI translator.\n\n"
        "Your task is to perform ONLY semantic translation.\n\n"
        "Rules:\n\n"
        "1. Detect the input language automatically.\n"
        "2. Translate the meaning into the selected target language.\n"
        "3. NEVER transliterate the text.\n"
        "4. NEVER return the pronunciation.\n"
        "5. NEVER return the original script.\n"
        "6. NEVER mix source language and target language.\n"
        "7. Translate naturally as a native speaker would say it.\n"
        "8. If the input is informal, slang, or spoken language, translate it into the closest natural expression.\n"
        "9. If there are spelling mistakes, understand the intended meaning and translate it correctly.\n"
        "10. Preserve the tone (formal, informal, emotional, polite, etc.).\n"
        "11. Return ONLY the translated text.\n"
        "12. Do not explain anything.\n"
        "13. Do not include notes.\n"
        "14. Do not include language names.\n"
        "15. Do not wrap the answer in quotes.\n\n"
        "Examples:\n\n"
        "Input:\n"
        "Source Language: Tamil\n"
        "Target Language: English\n"
        "Text:\n"
        "என்ன பண்ற?\n\n"
        "Output:\n"
        "What are you doing?\n\n"
        "------------------------\n\n"
        "Input:\n"
        "Source Language: Tamil\n"
        "Target Language: English\n"
        "Text:\n"
        "சாப்பிட்டியா?\n\n"
        "Output:\n"
        "Have you eaten?\n\n"
        "------------------------\n\n"
        "Input:\n"
        "Source Language: Tamil\n"
        "Target Language: English\n"
        "Text:\n"
        "நான் வீட்டுக்கு போறேன்\n\n"
        "Output:\n"
        "I'm going home.\n\n"
        "------------------------\n\n"
        "Input:\n"
        "Source Language: English\n"
        "Target Language: Tamil\n"
        "Text:\n"
        "How are you?\n\n"
        "Output:\n"
        "நீங்கள் எப்படி இருக்கிறீர்கள்?\n\n"
        "------------------------\n\n"
        "Input:\n"
        "Source Language: Hindi\n"
        "Target Language: English\n"
        "Text:\n"
        "आप कैसे हैं?\n\n"
        "Output:\n"
        "How are you?\n\n"
        "------------------------\n\n"
        "Input:\n"
        "Source Language: Telugu\n"
        "Target Language: Tamil\n"
        "Text:\n"
        "నువ్వు எக்கడికి వెళ్తున్నావు?\n\n"
        "Output:\n"
        "நீ எங்கே போகிறாய்?\n\n"
        "------------------------\n\n"
        "If the input language and target language are the same:\n"
        "Return the text with corrected spelling and grammar only.\n"
        "Do not translate.\n\n"
        "Always translate by meaning, never by pronunciation."
    )

    user_prompt = (
        f"Input:\n"
        f"Source Language: {source_name}\n"
        f"Target Language: {target_name}\n"
        f"Text:\n"
        f"{text}"
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
                temperature=0.3,
                timeout=20
            )
            return response.choices[0].message.content.strip()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI rate limit in text translation. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)
        except (APIConnectionError, APIStatusError) as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI API error in text translation: {str(e)}. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)
