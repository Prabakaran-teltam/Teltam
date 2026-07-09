import os
import time
import logging
from django.conf import settings
from pydub import AudioSegment
from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError
from app.services.openai_document_service import get_openai_client

logger = logging.getLogger(__name__)

def convert_audio_to_wav(input_path, output_path):
    """
    Converts any input audio file (WEBM, OGG, MP3, M4A, etc.) to a standard PCM WAV format.
    Requires ffmpeg to be installed on the system.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input audio file not found at: {input_path}")
        
    ext = os.path.splitext(input_path)[1].lower().replace('.', '')
    if not ext:
        ext = 'webm' # Fallback default
        
    logger.info(f"Converting audio file {input_path} (format: {ext}) to WAV...")
    
    # AudioSegment from_file dynamically determines format and delegates decoding to ffmpeg
    audio = AudioSegment.from_file(input_path, format=ext)
    
    # Export standard mono WAV at 16kHz sample rate (Whisper standard)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")
    logger.info(f"Exported WAV successfully to {output_path}")

def transcribe_audio_with_whisper(audio_path):
    """
    Transcribes audio using OpenAI's Whisper API.
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI client is not configured. Set OPENAI_API_KEY.")
        
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    logger.info(f"Sending audio file {audio_path} to OpenAI Whisper API...")
    
    max_retries = 3
    backoff = 2
    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcription.text.strip()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI rate limit hit. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)
        except (APIConnectionError, APIStatusError) as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"OpenAI API connection error: {str(e)}. Retrying in {backoff ** attempt}s...")
            time.sleep(backoff ** attempt)

def translate_voice_text(text, target_lang):
    """
    Translates the transcribed voice text into the target language using OpenAI.
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI client is not configured.")
        
    if not text or not text.strip():
        return ""
        
    system_prompt = (
        "You are a professional, high-accuracy conversational translator. "
        "Translate the input spoken text into the requested target language. "
        "Keep the spoken translation natural, colloquial, and match the original speaker's tone. "
        "Do not write any notes, commentary, or explanations. Return ONLY the translated spoken phrase."
    )
    user_prompt = f"Target Language: {target_lang}\n\nText to translate:\n{text}"
    
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
            time.sleep(backoff ** attempt)
        except (APIConnectionError, APIStatusError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff ** attempt)
    return ""
