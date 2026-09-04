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
def process_document_translation(self, history_id=None, temp_file_path=None, output_format='txt'):
    """
    Asynchronous Celery task / synchronous thread fallback that processes document translation using the OpenAI API.
    Updates the DocumentTranslationHistory model status and logs information.
    """
    from app.models import DocumentTranslationHistory
    from app.services.openai_document_service import (
        extract_text_from_image_with_openai,
        extract_text_from_multiple_images,
        extract_text_from_pdf,
        extract_text_from_docx,
        extract_text_from_txt,
        translate_text_with_openai,
        generate_translated_file
    )
    from django.core.files import File
    import traceback
    import json

    # Auto-align parameters based on invocation mode (.delay, .run, or direct call)
    task_instance = None
    if hasattr(self, 'request') and getattr(self.request, 'id', None) is not None:
        task_instance = self
    elif not isinstance(self, (int, str)):
        # Called via process_document_translation.run(history_id, temp_file_path, output_format)
        task_instance = None
    else:
        # Direct function call process_document_translation(history_id, temp_file_path, output_format)
        output_format = temp_file_path or 'txt'
        temp_file_path = history_id
        history_id = self
        task_instance = None

    def _set_progress(msg):
        if task_instance:
            try:
                task_instance.update_state(state='PROGRESS', meta={'status': msg})
            except Exception:
                pass

    try:
        # Fetch the history record
        history = DocumentTranslationHistory.objects.get(id=int(history_id))
    except (DocumentTranslationHistory.DoesNotExist, ValueError, TypeError) as err:
        logger.error(f"DocumentTranslationHistory with id {history_id} not found or invalid: {err}")
        return {'status': 'FAILURE', 'error': 'Translation history record not found.'}

    # Mark status as processing
    history.status = 'processing'
    history.save()

    _set_progress('Extracting document text...')

    # Parse multi-file path list if passed as JSON string
    file_paths_list = []
    if isinstance(temp_file_path, str) and temp_file_path.strip().startswith('['):
        try:
            file_paths_list = json.loads(temp_file_path)
        except Exception:
            file_paths_list = [temp_file_path]
    elif isinstance(temp_file_path, list):
        file_paths_list = temp_file_path
    else:
        file_paths_list = [temp_file_path]

    extracted_text = ""

    try:
        # 1. Text Extraction
        if len(file_paths_list) > 1:
            _set_progress(f'Extracting text from {len(file_paths_list)} images via AI Vision OCR...')
            extracted_text = extract_text_from_multiple_images(file_paths_list)
        else:
            single_path = file_paths_list[0]
            ext = os.path.splitext(single_path)[1].lower()
            if ext == '.txt':
                extracted_text = extract_text_from_txt(single_path)
            elif ext == '.pdf':
                extracted_text = extract_text_from_pdf(single_path)
            elif ext == '.docx':
                extracted_text = extract_text_from_docx(single_path)
            elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                extracted_text = extract_text_from_image_with_openai(single_path)
            else:
                raise ValueError(f"Unsupported file format {ext}")

        if not extracted_text.strip():
            extracted_text = f"[Empty Document: No text could be extracted]"

        # Update history with extracted text
        history.extracted_text = extracted_text
        history.save()

        # 2. Translation
        _set_progress('Translating text with OpenAI...')

        translated_text = translate_text_with_openai(
            text=extracted_text,
            target_lang=history.target_language,
            source_lang=history.source_language
        )

        # Generate OpenAI Transliteration (Phonetic pronunciation guide)
        transliteration = ""
        try:
            from app.services.openai_text_service import generate_transliteration_with_openai
            transliteration = generate_transliteration_with_openai(translated_text, target_lang=history.target_language)
        except Exception as translit_err:
            logger.warning(f"Failed to generate document transliteration: {str(translit_err)}")

        history.translated_text = translated_text
        history.transliterated_text = transliteration
        history.save()

        # 3. Generate result file
        _set_progress('Generating translated document...')

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
            'transliteration': transliteration,
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
        # Clean up temporary input files
        for p in file_paths_list:
            if isinstance(p, str) and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as clean_err:
                    logger.warning(f"Failed to delete temp file {p}: {str(clean_err)}")

@shared_task(bind=True)
def process_voice_translation(self, temp_file_path, target_lang, user_id=None):
    """
    Asynchronous task to transcribe audio files using OpenAI Whisper,
    translate the transcribed text, generate transliteration, and clean up.
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

        # Generate OpenAI Transliteration (Phonetic pronunciation guide)
        transliteration = ""
        try:
            from app.services.openai_text_service import generate_transliteration_with_openai
            transliteration = generate_transliteration_with_openai(translated_text, target_lang=target_lang)
        except Exception as translit_err:
            logger.warning(f"Failed to generate voice transliteration: {str(translit_err)}")
        
        # Log to User Translation History
        if user_id:
            try:
                from django.contrib.auth.models import User
                from app.models import UserTranslationHistory
                user = User.objects.get(id=user_id)
                UserTranslationHistory.objects.create(
                    user=user,
                    tool_type='voice',
                    source_text=f"[Audio Transcript] {transcription}",
                    translated_text=translated_text,
                    transliterated_text=transliteration,
                    source_lang="auto",
                    target_lang=target_lang,
                    file_name=os.path.basename(temp_file_path)
                )
            except Exception as hist_err:
                logger.warning(f"Failed to save voice translation history: {str(hist_err)}")

        return {
            'status': 'SUCCESS',
            'transcription': transcription,
            'translated_text': translated_text,
            'transliteration': transliteration
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


@shared_task(bind=True)
def send_new_blog_notifications_task(self, blog_id):
    """
    Asynchronous mass email task that sends HTML notification to 100+ registered users
    whenever a new blog is published by the admin.

    Features for 100+ scale stability:
    1. Retrieves active user email addresses without loading full User objects into memory.
    2. Batches emails in chunks of 50 recipients using connection reuse (get_connection()).
    3. Uses BCC mass mailing so recipient addresses are kept private.
    4. Handles exceptions with fail_silently=True and updates blog.is_notification_sent=True.
    """
    from app.models import Blog
    from django.contrib.auth.models import User
    from django.core.mail import EmailMultiAlternatives, get_connection
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.urls import reverse

    try:
        blog = Blog.objects.get(id=blog_id, is_published=True)
    except Blog.DoesNotExist:
        logger.warning(f"Blog with id {blog_id} not found or not published.")
        return {'status': 'SKIPPED', 'message': 'Blog not found or not published'}

    # If notification already sent, prevent duplicate sending
    if blog.is_notification_sent:
        logger.info(f"Notification already sent for blog ID {blog_id}. Skipping.")
        return {'status': 'SKIPPED', 'message': 'Notification already sent'}

    # Get active registered user emails
    recipient_emails = list(
        User.objects.filter(is_active=True)
        .exclude(email='')
        .exclude(email__isnull=True)
        .values_list('email', flat=True)
        .distinct()
    )

    if not recipient_emails:
        logger.info("No registered users with valid email addresses found.")
        blog.is_notification_sent = True
        blog.save(update_fields=['is_notification_sent'])
        return {'status': 'SUCCESS', 'sent_count': 0}

    site_url = getattr(settings, 'SITE_URL', 'https://teltam.in').rstrip('/')
    blog_path = reverse('blog_view', kwargs={'slug': blog.slug})
    blog_url = f"{site_url}{blog_path}"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Teltam AI <info@teltam.in>')

    # Render HTML and plain text email content
    html_content = render_to_string('emails/new_blog_notification.html', {
        'blog': blog,
        'blog_url': blog_url,
        'site_url': site_url
    })
    plain_content = strip_tags(html_content)

    subject = f"🔔 New Article: {blog.title} - Teltam AI"

    # Batch recipients in groups of 50 to ensure high SMTP stability & rate-limit compliance
    batch_size = 50
    total_sent = 0

    try:
        connection = get_connection(fail_silently=True)
        try:
            connection.open()
        except Exception as conn_err:
            logger.warning(f"Could not open SMTP connection: {conn_err}")

        for i in range(0, len(recipient_emails), batch_size):
            batch = recipient_emails[i:i + batch_size]

            # Build multi-alternative email message with BCC to preserve privacy
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_content,
                from_email=from_email,
                to=[from_email],
                bcc=batch,
                connection=connection
            )
            msg.attach_alternative(html_content, "text/html")
            
            try:
                sent = connection.send_messages([msg])
                total_sent += len(batch)
            except Exception as batch_err:
                logger.exception(f"Error sending email batch {i // batch_size + 1}: {batch_err}")

        try:
            connection.close()
        except Exception:
            pass

        # Mark notification as sent
        blog.is_notification_sent = True
        blog.save(update_fields=['is_notification_sent'])

        logger.info(f"Successfully dispatched new blog notification emails to {total_sent} registered users for blog ID {blog_id}.")
        return {'status': 'SUCCESS', 'sent_count': total_sent}

    except Exception as e:
        logger.exception(f"Failed mass email dispatch for blog ID {blog_id}: {str(e)}")
        return {'status': 'FAILURE', 'error': str(e)}


@shared_task
def check_and_dispatch_scheduled_blogs_task():
    """
    Periodic task / helper to check for published blogs whose scheduled date/time has arrived
    and send their email notifications if not yet sent.
    """
    from app.models import Blog
    from django.utils import timezone

    now = timezone.now()
    due_blogs = Blog.objects.filter(
        is_published=True,
        send_email_notification=True,
        is_notification_sent=False,
        scheduled_publish_date__isnull=False,
        scheduled_publish_date__lte=now
    )

    dispatched_count = 0
    for blog in due_blogs:
        try:
            logger.info(f"Dispatching scheduled blog notification for blog ID {blog.id} ('{blog.title}').")
            send_new_blog_notifications_task(blog.id)
            dispatched_count += 1
        except Exception as err:
            logger.exception(f"Failed to dispatch scheduled notification for blog ID {blog.id}: {err}")

    return {'status': 'SUCCESS', 'dispatched_count': dispatched_count}



