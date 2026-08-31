import os
import re
import io
import time
import asyncio
import hashlib
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Microsoft Neural Voice Mapping per language locale (Optimized for perfect Tamil & Indian pronunciation)
AZURE_VOICE_MAP = {
    'ta': 'ta-IN-PallaviNeural',
    'ta-in': 'ta-IN-PallaviNeural',
    'en': 'en-IN-NeerjaNeural',
    'en-in': 'en-IN-NeerjaNeural',
    'en-us': 'en-US-JennyNeural',
    'hi': 'hi-IN-SwaraNeural',
    'hi-in': 'hi-IN-SwaraNeural',
    'te': 'te-IN-ShrutiNeural',
    'te-in': 'te-IN-ShrutiNeural',
    'ml': 'ml-IN-SobhanaNeural',
    'ml-in': 'ml-IN-SobhanaNeural',
    'kn': 'kn-IN-SapnaNeural',
    'kn-in': 'kn-IN-SapnaNeural',
    'mr': 'mr-IN-AarohiNeural',
    'mr-in': 'mr-IN-AarohiNeural',
    'bn': 'bn-IN-TanishaaNeural',
    'bn-in': 'bn-IN-TanishaaNeural',
    'gu': 'gu-IN-DhwaniNeural',
    'gu-in': 'gu-IN-DhwaniNeural',
    'es': 'es-ES-ElviraNeural',
    'fr': 'fr-FR-DeniseNeural',
    'de': 'de-DE-KatjaNeural',
    'zh': 'zh-CN-XiaoxiaoNeural',
    'ja': 'ja-JP-NanamiNeural',
    'ko': 'ko-KR-SunHiNeural',
    'ar': 'ar-SA-ZariyahNeural',
}

def clean_text_for_tts(text: str) -> str:
    """Strips HTML tags, markdown symbols, and normalizes whitespace for crisp speech output."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    # Strip markdown symbols
    cleaned = re.sub(r'[\*\#\_\[\]\(\)\`\~]+', ' ', cleaned)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def get_azure_voice(language_code: str) -> tuple:
    """Returns (azure_voice_name, locale_code) based on requested language."""
    clean_lang = (language_code or 'en').strip().lower().replace('_', '-')
    voice_name = AZURE_VOICE_MAP.get(clean_lang)
    if not voice_name:
        prefix = clean_lang.split('-')[0]
        voice_name = AZURE_VOICE_MAP.get(prefix, 'en-IN-NeerjaNeural')
    
    locale_code = voice_name.rsplit('-', 1)[0]
    return voice_name, locale_code

def chunk_text(text: str, max_chars: int = 800) -> list:
    """Splits long text into sentence-aware safe chunks for TTS synthesis."""
    if len(text) <= max_chars:
        return [text]
    
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk = (current_chunk + " " + sentence).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks if chunks else [text[:max_chars]]

def _synthesize_edge_tts_sync(text: str, voice: str) -> bytes:
    """Helper to synthesize audio using edge-tts asynchronously inside a sync wrapper."""
    import edge_tts
    async def _async_synth():
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(_async_synth())
        loop.close()
        return res
    except Exception as err:
        logger.warning(f"Edge TTS async loop error: {err}")
        return b""

def generate_neural_tts_audio(text: str, language_code: str = 'en') -> dict:
    """
    Generates high-quality Neural MP3 Audio using Microsoft Edge Neural TTS with Azure Speech SDK, OpenAI HD & gTTS fallbacks.
    Implements SHA-256 disk caching under MEDIA_ROOT/tts/.
    """
    start_ts = time.time()
    clean_text = clean_text_for_tts(text)
    if not clean_text:
        return {"success": False, "error": "Empty or invalid text provided."}

    voice_name, locale_code = get_azure_voice(language_code)

    # 1. SHA-256 Cache Key Calculation
    cache_string = f"{clean_text}_{locale_code}_{voice_name}".encode('utf-8')
    audio_hash = hashlib.sha256(cache_string).hexdigest()[:24]
    
    media_root = Path(getattr(settings, 'MEDIA_ROOT', 'media'))
    tts_dir = media_root / 'tts'
    tts_dir.mkdir(parents=True, exist_ok=True)
    
    mp3_filename = f"{audio_hash}.mp3"
    mp3_filepath = tts_dir / mp3_filename
    
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    audio_relative_url = f"{media_url}tts/{mp3_filename}"

    # 2. Check Disk Cache (Instant < 5ms response!)
    if mp3_filepath.exists() and mp3_filepath.stat().st_size > 100:
        logger.info(f"TTS Disk Cache Hit ({time.time() - start_ts:.3f}s): {audio_relative_url}")
        return {
            "success": True,
            "status": "success",
            "audio_url": audio_relative_url,
            "language": locale_code,
            "voice": voice_name,
            "cached": True
        }

    # Split into chunks if text is long
    chunks = chunk_text(clean_text)
    audio_chunks_bytes = []

    # Tier 1: Primary OpenAI gpt-4o-mini-tts Engine (ChatGPT API Key)
    openai_model = getattr(settings, 'OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
    try:
        from app.services.openai_document_service import get_openai_client
        openai_client = get_openai_client()
        if openai_client:
            for chunk in chunks:
                response = openai_client.audio.speech.create(
                    model=openai_model,
                    voice="nova",  # Warm studio-quality natural speaking voice
                    input=chunk,
                    speed=1.0
                )
                audio_chunks_bytes.append(response.content)
            logger.info(f"OpenAI {openai_model} TTS generated audio successfully.")
    except Exception as openai_err:
        logger.warning(f"OpenAI {openai_model} TTS failed, attempting Edge Neural fallback: {openai_err}")
        audio_chunks_bytes = []

    # Tier 2: Microsoft Edge Neural TTS Fallback
    if not audio_chunks_bytes:
        try:
            for chunk in chunks:
                data = _synthesize_edge_tts_sync(chunk, voice_name)
                if data and len(data) > 100:
                    audio_chunks_bytes.append(data)
                else:
                    audio_chunks_bytes = []
                    break
        except Exception as edge_err:
            logger.warning(f"Edge TTS tier 2 failed: {edge_err}")
            audio_chunks_bytes = []

    # Tier 2: Azure Neural Speech SDK Synthesizer (If credentials set)
    if not audio_chunks_bytes:
        azure_key = getattr(settings, 'AZURE_SPEECH_KEY', None) or os.environ.get('AZURE_SPEECH_KEY')
        azure_region = getattr(settings, 'AZURE_SPEECH_REGION', 'eastus') or os.environ.get('AZURE_SPEECH_REGION', 'eastus')
        if azure_key:
            try:
                import azure.cognitiveservices.speech as speechsdk
                speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
                speech_config.speech_synthesis_voice_name = voice_name
                speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                )

                for chunk in chunks:
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                    result = synthesizer.speak_text_async(chunk).get()
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        audio_chunks_bytes.append(result.audio_data)
                    else:
                        logger.warning(f"Azure Speech Synthesis Chunk failed: {result.reason}")
                        audio_chunks_bytes = []
                        break
            except Exception as azure_err:
                logger.warning(f"Azure Speech SDK failed: {azure_err}")
                audio_chunks_bytes = []

    # Tier 3: OpenAI tts-1-hd Fallback
    if not audio_chunks_bytes:
        try:
            from app.services.openai_document_service import get_openai_client
            openai_client = get_openai_client()
            if openai_client:
                for chunk in chunks:
                    response = openai_client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=chunk,
                        speed=1.0
                    )
                    audio_chunks_bytes.append(response.content)
        except Exception as openai_err:
            logger.warning(f"OpenAI TTS fallback failed: {openai_err}")
            audio_chunks_bytes = []

    # Tier 4: gTTS Fallback
    if not audio_chunks_bytes:
        try:
            from gtts import gTTS
            lang_prefix = locale_code.split('-')[0].lower()
            gtts_lang_map = {'zh': 'zh-CN', 'zh-cn': 'zh-CN', 'zh-tw': 'zh-TW'}
            gtts_lang = gtts_lang_map.get(lang_prefix, lang_prefix)
            
            for chunk in chunks:
                try:
                    tts = gTTS(text=chunk, lang=gtts_lang, slow=False)
                except Exception as lang_err:
                    logger.warning(f"gTTS failed for language {gtts_lang}, falling back to English: {lang_err}")
                    tts = gTTS(text=chunk, lang='en', slow=False)
                
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_chunks_bytes.append(fp.getvalue())
        except Exception as gtts_err:
            logger.error(f"gTTS fallback failed completely: {gtts_err}")
            audio_chunks_bytes = []

    # Write combined MP3 binary bytes to cache file
    if audio_chunks_bytes:
        try:
            with open(mp3_filepath, 'wb') as f:
                for chunk_b in audio_chunks_bytes:
                    f.write(chunk_b)

            logger.info(f"Generated TTS audio saved in {time.time() - start_ts:.3f}s: {mp3_filepath}")
            return {
                "success": True,
                "status": "success",
                "audio_url": audio_relative_url,
                "language": locale_code,
                "voice": voice_name,
                "cached": False
            }
        except Exception as write_err:
            logger.error(f"Failed to write TTS mp3 file: {write_err}")
            return {"success": False, "error": "Disk write error saving audio."}

    return {"success": False, "error": "Audio generation returned empty result."}
