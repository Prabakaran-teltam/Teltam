import os
import uuid
import logging
from django.conf import settings
from celery import shared_task
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)



def translate_chunks(text, source_lang, target_lang):
    """
    Translates text in chunks of 2000 characters to avoid API limits.
    """
    if not text:
        return ""
    
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    
    # Split text by paragraphs or lines to avoid breaking words
    parts = text.split('\n')
    translated_parts = []
    current_chunk = []
    current_length = 0
    
    for part in parts:
        if current_length + len(part) + 1 > 2000:
            # Translate current chunk
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                translated_parts.append(translator.translate(chunk_text))
            current_chunk = [part]
            current_length = len(part)
        else:
            current_chunk.append(part)
            current_length += len(part) + 1
            
    if current_chunk:
        chunk_text = '\n'.join(current_chunk)
        if chunk_text.strip():
            translated_parts.append(translator.translate(chunk_text))
            
    return '\n'.join(translated_parts)

@shared_task(bind=True)
def process_document_translation(self, history_id, temp_file_path, output_format):
    """
    Asynchronous Celery task that processes document translation using the OpenAI API.
    Updates the DocumentTranslationHistory model status and logs information.
    """
    from app.models import DocumentTranslationHistory
    from app.services.openai_document_service import (
        extract_text_from_image_with_openai,
        extract_text_from_pdf,
        extract_text_from_docx,
        extract_text_from_txt,
        translate_text_with_openai,
        generate_translated_file
    )
    from django.core.files import File
    import traceback

    try:
        # Fetch the history record
        history = DocumentTranslationHistory.objects.get(id=history_id)
    except DocumentTranslationHistory.DoesNotExist:
        logger.error(f"DocumentTranslationHistory with id {history_id} not found.")
        return {'status': 'FAILURE', 'error': 'Translation history record not found.'}

    # Mark status as processing
    history.status = 'processing'
    history.save()

    if self.request.id:
        self.update_state(state='PROGRESS', meta={'status': 'Extracting document text...'})

    ext = os.path.splitext(temp_file_path)[1].lower()
    extracted_text = ""

    try:
        # 1. Text Extraction
        if ext == '.txt':
            extracted_text = extract_text_from_txt(temp_file_path)
        elif ext == '.pdf':
            extracted_text = extract_text_from_pdf(temp_file_path)
        elif ext == '.docx':
            extracted_text = extract_text_from_docx(temp_file_path)
        elif ext in ['.jpg', '.jpeg', '.png']:
            extracted_text = extract_text_from_image_with_openai(temp_file_path)
        else:
            raise ValueError(f"Unsupported file format {ext}")

        if not extracted_text.strip():
            extracted_text = f"[Empty Document: No text could be extracted from {os.path.basename(temp_file_path)}]"

        # Update history with extracted text
        history.extracted_text = extracted_text
        history.save()

        # 2. Translation
        if self.request.id:
            self.update_state(state='PROGRESS', meta={'status': 'Translating text with OpenAI...'})

        translated_text = translate_text_with_openai(
            text=extracted_text,
            target_lang=history.target_language,
            source_lang=history.source_language
        )

        history.translated_text = translated_text
        history.save()

        # 3. Generate result file
        if self.request.id:
            self.update_state(state='PROGRESS', meta={'status': 'Generating translated document...'})

        downloads_dir = os.path.join(settings.MEDIA_ROOT, 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)

        output_filename = f"translated_{uuid.uuid4().hex}.{output_format}"
        output_path = os.path.join(downloads_dir, output_filename)

        generate_translated_file(translated_text, output_format, output_path, target_lang=history.target_language)

        # Save to database FileField
        with open(output_path, 'rb') as f:
            history.download_file.save(output_filename, File(f), save=True)

        # Update status to success
        history.status = 'success'
        history.save()

        # Clean up temporary output file
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        # Return download URL
        from django.urls import reverse
        download_url = reverse('download_translated_file', kwargs={'id': history.id})

        return {
            'status': 'SUCCESS',
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'download_url': download_url
        }

    except Exception as e:
        logger.exception("Error processing document translation")
        error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        history.status = 'failure'
        history.error_message = error_msg
        history.save()

        return {
            'status': 'FAILURE',
            'error': str(e)
        }

    finally:
        # Clean up temporary input file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as clean_err:
                logger.warning(f"Failed to delete temp file {temp_file_path}: {str(clean_err)}")

@shared_task(bind=True)
def process_voice_translation(self, temp_file_path, target_lang, user_id=None):
    """
    Asynchronous task to transcribe audio files using OpenAI Whisper,
    translate the transcribed text, and clean up.
    """
    if self.request.id:
        self.update_state(state='PROGRESS', meta={'status': 'Transcribing speech to text...'})
    
    converted_wav_path = None
    try:
        from app.services.openai_voice_service import convert_audio_to_wav, transcribe_audio_with_whisper, translate_voice_text
        
        # Attempt audio conversion to WAV first for standardizing to mono 16kHz.
        # If conversion fails (e.g. ffmpeg missing), fall back to direct processing.
        temp_dir = os.path.dirname(temp_file_path)
        converted_wav_path = os.path.join(temp_dir, f"converted_{uuid.uuid4().hex}.wav")
        
        transcribe_path = temp_file_path
        try:
            if self.request.id:
                self.update_state(state='PROGRESS', meta={'status': 'Converting audio format...'})
            convert_audio_to_wav(temp_file_path, converted_wav_path)
            transcribe_path = converted_wav_path
        except Exception as conv_err:
            logger.warning(f"Audio conversion to WAV failed, attempting fallback directly with original file: {str(conv_err)}")
            transcribe_path = temp_file_path
            
        if self.request.id:
            self.update_state(state='PROGRESS', meta={'status': 'Transcribing speech with Whisper...'})
            
        transcription = transcribe_audio_with_whisper(transcribe_path)
        
        # Translate the transcribed text
        if self.request.id:
            self.update_state(state='PROGRESS', meta={'status': 'Translating transcribed voice...'})
        
        translated_text = translate_voice_text(transcription, target_lang)
        
        # Log to User Translation History
        if user_id:
            try:
                from django.contrib.auth.models import User
                from app.models import UserTranslationHistory
                user = User.objects.get(id=user_id)
                UserTranslationHistory.objects.create(
                    user=user,
                    tool_type='voice',
                    source_text="Recorded/Uploaded Voice Audio",
                    translated_text=f"Transcription: {transcription}\nTranslation: {translated_text}",
                    source_lang="auto",
                    target_lang=target_lang,
                    file_name=os.path.basename(temp_file_path)
                )
            except Exception as hist_err:
                logger.warning(f"Failed to save voice translation history: {str(hist_err)}")

        return {
            'status': 'SUCCESS',
            'transcription': transcription,
            'translated_text': translated_text
        }
        
    except Exception as e:
        logger.exception("Error processing voice translation task")
        return {
            'status': 'FAILURE',
            'error': str(e)
        }
    finally:
        # Clean up temporary audio files
        for path in [temp_file_path, converted_wav_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as clean_err:
                    logger.warning(f"Failed to delete temp file {path}: {str(clean_err)}")

