import os
import time
import logging
from django.conf import settings
from pydub import AudioSegment
from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError
from app.services.openai_document_service import get_openai_client

logger = logging.getLogger(__name__)

import subprocess

def convert_audio_to_wav(input_path, output_path):
    """
    Converts any input audio/video recording file (WAV, MP3, M4A, WEBM, OGG, FLAC, AAC, OPUS, WMA, AIFF, AMR, MP4, 3GP, etc.)
    to a standard PCM WAV format (16kHz, 1 channel).
    Uses multi-stage fallback (Pydub auto-detect -> Pydub format hint -> direct FFmpeg subprocess).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input audio file not found at: {input_path}")
        
    ext = os.path.splitext(input_path)[1].lower().replace('.', '')
    logger.info(f"Converting audio file {input_path} (format extension: '{ext}') to WAV...")

    # Method 1: Pydub auto-detecting format without forcing format string parameter
    try:
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format="wav")
        logger.info(f"Exported WAV successfully via Pydub auto-detect to {output_path}")
        return
    except Exception as err1:
        logger.warning(f"Pydub auto-detect failed for {input_path}: {err1}")

    # Method 2: Pydub with explicit format hint
    if ext:
        try:
            audio = AudioSegment.from_file(input_path, format=ext)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(output_path, format="wav")
            logger.info(f"Exported WAV successfully via Pydub format hint '{ext}' to {output_path}")
            return
        except Exception as err2:
            logger.warning(f"Pydub format hint '{ext}' failed for {input_path}: {err2}")

    # Method 3: Direct FFmpeg subprocess execution fallback
    try:
        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-ar', '16000',
            '-ac', '1',
            '-f', 'wav',
            output_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Exported WAV successfully via direct FFmpeg subprocess to {output_path}")
            return
        else:
            logger.warning(f"Direct FFmpeg subprocess returned code {result.returncode}: {result.stderr}")
    except Exception as ffmpeg_err:
        logger.warning(f"Direct FFmpeg subprocess execution failed for {input_path}: {ffmpeg_err}")

    raise ValueError(f"Could not convert audio file '{input_path}' to WAV format using Pydub or FFmpeg.")

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
