import os
import uuid
import json
import hashlib
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.cache import cache
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def home(request):
    """Renders the Home page."""
    return render(request, 'index.html')

def about(request):
    """Renders the About page."""
    return render(request, 'about.html')

def services(request):
    """Renders the Services page."""
    return render(request, 'services.html')

def pricing(request):
    """Renders the Pricing page."""
    populate_default_plans()
    active_plan = None
    active_plan_order = 0
    if request.user.is_authenticated:
        active_sub = UserSubscription.objects.filter(user=request.user, status='active').first()
        if active_sub and active_sub.plan:
            active_plan = active_sub.plan
            active_plan_order = active_sub.plan.plan_order
            if active_plan_order < 3:
                messages.info(request, "Upgrades are available for higher plans.")
            else:
                messages.info(request, "You are on the highest plan.")

    context = {
        'active_plan_slug': active_plan.slug if active_plan else None,
        'active_plan_order': active_plan_order,
        'allow_downgrade': getattr(settings, 'ALLOW_DOWNGRADE', False),
    }
    return render(request, 'pricing.html', context)

@ensure_csrf_cookie
def ai_tools(request):
    """Renders the AI Tools page."""
    return render(request, 'ai-tools.html')

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import base64

from .models import Blog, YoutubeVideo, Contact, UserTranslationHistory, PricingPlan, UserSubscription, PaymentTransaction, DocumentTranslationHistory
from .forms import BlogForm, YoutubeVideoForm, ContactForm, UserProfileForm
from .phonepe_service import PhonePeService


def blog_list(request):
    """Renders the Blog listing page with dynamic DB search, category filter, and pagination."""
    blogs_query = Blog.objects.filter(is_published=True)
    
    # 1. Category filter
    category = request.GET.get('category', '').strip()
    if category:
        blogs_query = blogs_query.filter(category__iexact=category)
        
    # 2. Search filter
    q = request.GET.get('q', '').strip()
    if q:
        blogs_query = blogs_query.filter(
            Q(title__icontains=q) | 
            Q(short_description__icontains=q) | 
            Q(full_content__icontains=q) |
            Q(tags__icontains=q)
        )
        
    # 3. Pagination
    paginator = Paginator(blogs_query, 6) # 6 blogs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 4. Sidebar components
    recent_blogs = Blog.objects.filter(is_published=True).order_by('-created_date')[:3]
    categories = Blog.objects.filter(is_published=True).values_list('category', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'recent_blogs': recent_blogs,
        'categories': categories,
        'selected_category': category,
        'search_query': q,
    }
    return render(request, 'blog-list.html', context)

def blog_view(request, slug):
    """Renders the detailed Blog article view page using slug lookup."""
    blog = get_object_or_404(Blog, slug=slug, is_published=True)
    recent_blogs = Blog.objects.filter(is_published=True).exclude(id=blog.id).order_by('-created_date')[:3]
    
    context = {
        'blog': blog,
        'recent_blogs': recent_blogs,
    }
    return render(request, 'blog-view.html', context)

def video_list(request):
    """Renders the YouTube video listing page with search, categories, and pagination."""
    videos_query = YoutubeVideo.objects.filter(is_published=True)
    
    # Category filter
    category = request.GET.get('category', '').strip()
    if category:
        videos_query = videos_query.filter(category__iexact=category)
        
    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        videos_query = videos_query.filter(
            Q(title__icontains=q) | 
            Q(short_description__icontains=q) |
            Q(tags__icontains=q)
        )
        
    # Pagination
    paginator = Paginator(videos_query, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Sidebar components
    recent_videos = YoutubeVideo.objects.filter(is_published=True).order_by('-created_date')[:3]
    categories = YoutubeVideo.objects.filter(is_published=True).values_list('category', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'recent_videos': recent_videos,
        'categories': categories,
        'selected_category': category,
        'search_query': q,
    }
    return render(request, 'video-list.html', context)

def video_view(request, slug):
    """Renders the detailed YouTube video view page."""
    video = get_object_or_404(YoutubeVideo, slug=slug, is_published=True)
    recent_videos = YoutubeVideo.objects.filter(is_published=True).exclude(id=video.id).order_by('-created_date')[:3]
    
    context = {
        'video': video,
        'recent_videos': recent_videos,
    }
    return render(request, 'video-view.html', context)

def contact(request):
    """Saves Contact Us form submissions to DB and displays validation alerts."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        # Validation checks
        if not name or len(name) < 2:
            messages.error(request, "Please enter a valid name (min 2 characters).")
        elif not email or '@' not in email:
            messages.error(request, "Please enter a valid email address.")
        elif not subject:
            messages.error(request, "Please enter a subject line.")
        elif not message or len(message) < 10:
            messages.error(request, "Please enter a message (min 10 characters).")
        else:
            try:
                Contact.objects.create(
                    name=name, email=email, phone=phone, subject=subject, message=message
                )
                messages.success(request, f"Thank you, {name}! Your message has been sent successfully. We will get back to you shortly.")
                return redirect('contact')
            except Exception as e:
                logger.exception("Failed to save contact message")
                messages.error(request, "An error occurred while sending your message. Please try again.")
                
    return render(request, 'contact.html')

def login_view(request):
    """Handles standard user Sign In authentication."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.user.is_authenticated:
        selected_plan_slug = request.session.get('selected_plan_slug')
        if selected_plan_slug:
            del request.session['selected_plan_slug']
            return redirect('checkout', plan_slug=selected_plan_slug)
        if next_url:
            return redirect(next_url)
        return redirect('user_dashboard_home')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, "Please fill in all credentials.")
        else:
            # Query user by email first
            user_obj = User.objects.filter(email=email).first()
            username = user_obj.username if user_obj else email
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Welcome back to Teltam AI!")
                selected_plan_slug = request.session.get('selected_plan_slug')
                if selected_plan_slug:
                    del request.session['selected_plan_slug']
                    return redirect('checkout', plan_slug=selected_plan_slug)
                if next_url:
                    return redirect(next_url)
                return redirect('user_dashboard_home')
            else:
                messages.error(request, "Invalid email address or password.")
                
    return render(request, 'login.html', {'next': next_url})

def register_view(request):
    """Handles standard user registration form posts."""
    if request.user.is_authenticated:
        return redirect('user_dashboard_home')
        
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        agree_terms = request.POST.get('agree_terms')
        
        # Validations
        if not name or len(name) < 2:
            messages.error(request, "Full name must be at least 2 characters.")
        elif not email or '@' not in email:
            messages.error(request, "Please enter a valid email address.")
        elif len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif not agree_terms:
            messages.error(request, "You must agree to the Terms of Service.")
        elif User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email address already exists.")
        else:
            try:
                # Use email as the username
                user = User.objects.create_user(
                    username=email, email=email, password=password, first_name=name
                )
                messages.success(request, "Registration successful! You can now log in.")
                return redirect('login')
            except Exception as e:
                logger.exception("Failed to create user during registration")
                messages.error(request, "Failed to create account. Please try again.")
                
    return render(request, 'register.html')

def logout_view(request):
    """Logs the user out of their session."""
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def validate_language_codes(source_lang, target_lang, allow_source_auto=True):
    """
    Validates source and target language codes against the centralized 200+ list.
    """
    from app.constants import LANGUAGES
    valid_codes = {lang['code'] for lang in LANGUAGES}
    
    if allow_source_auto and source_lang == 'auto':
        pass
    elif source_lang not in valid_codes:
        return False, f"Unsupported or invalid source language: '{source_lang}'"
        
    if target_lang not in valid_codes:
        return False, f"Unsupported or invalid target language: '{target_lang}'"
        
    return True, None

@require_POST
def translate_api(request):
    """
    POST API endpoint for live translation.
    Expects JSON request body with:
      - text: string to translate
      - source_lang: string (e.g. 'en', 'es', or 'auto')
      - target_lang: string (e.g. 'es', 'fr', etc.)
    Returns JSON response.
    """
    # 1. Rate limiting check (using cache)
    ip = get_client_ip(request)
    rate_limit_key = f"rate_limit_{ip}"
    request_count = cache.get(rate_limit_key, 0)
    
    # 60 requests per minute per IP
    if request_count >= 60:
        return JsonResponse({
            'error': 'Rate limit exceeded. Please wait a moment before trying again.'
        }, status=429)
    
    cache.set(rate_limit_key, request_count + 1, timeout=60)
    
    # 2. Parse request payload
    try:

        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON request payload'}, status=400)
        
    text = data.get('text', '').strip()
    source_lang = data.get('source_lang', 'auto').strip()
    target_lang = data.get('target_lang', 'es').strip()
    
    # 3. Validation
    if not text:
        return JsonResponse({'error': 'Text to translate is required.'}, status=400)
        
    if len(text) > 5000:
        return JsonResponse({'error': 'Text exceeds the maximum limit of 5000 characters.'}, status=400)

    # Validate language codes
    is_valid, err_msg = validate_language_codes(source_lang, target_lang, allow_source_auto=True)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)
        
    # 4. Check cache for repeated translations
    cache_input = f"{source_lang}:{target_lang}:{text}"
    cache_key = f"teltam_translation_{hashlib.md5(cache_input.encode('utf-8')).hexdigest()}"
    cached_response = cache.get(cache_key)
    
    if cached_response:
        if request.user.is_authenticated:
            try:
                UserTranslationHistory.objects.create(
                    user=request.user,
                    tool_type='text',
                    source_text=text,
                    translated_text=cached_response.get('translated_text'),
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            except Exception as e:
                logger.warning(f"Failed to log cached text translation: {str(e)}")
        return JsonResponse(cached_response)
        
    # 5. Perform translation and transliteration
    try:
        # Translate via Google Translate scraper interface (deep-translator)
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated_text = translator.translate(text)
        
        response_data = {
            'translated_text': translated_text,
            'source_lang': source_lang,
            'target_lang': target_lang
        }
        
        # Save to cache for 24 hours (86400 seconds)
        cache.set(cache_key, response_data, timeout=86400)
        
        # Save translation history
        if request.user.is_authenticated:
            try:
                UserTranslationHistory.objects.create(
                    user=request.user,
                    tool_type='text',
                    source_text=text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            except Exception as e:
                logger.warning(f"Failed to log text translation: {str(e)}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception("Live translation view encountered an error")
        return JsonResponse({
            'error': 'Translation service is currently unavailable. Please try again.'
        }, status=500)

from celery.result import AsyncResult
from django.conf import settings
from django.views.decorators.http import require_GET

@require_POST
def upload_document(request):
    """
    POST API to upload a document for translation.
    Rate limits to 5 uploads per minute.
    Creates a DocumentTranslationHistory record and queues Celery task.
    Returns Celery task ID and history ID immediately.
    """
    # Ensure OpenAI API key is configured
    if not getattr(settings, 'OPENAI_API_KEY', None):
        return JsonResponse({'error': 'OpenAI API client is not configured. Please set OPENAI_API_KEY.'}, status=500)

    # Check authentication settings
    if not request.user.is_authenticated:
        if not getattr(settings, 'ALLOW_ANONYMOUS_TRANSLATION', False):
            return JsonResponse({'error': 'You must be logged in to translate documents.'}, status=401)

    # Rate limiting
    ip = get_client_ip(request)
    limit_key = f"rate_limit_upload_doc_{ip}"
    count = cache.get(limit_key, 0)
    if count >= 5:
        return JsonResponse({'error': 'Too many document uploads. Please wait a minute.'}, status=429)
    cache.set(limit_key, count + 1, timeout=60)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    uploaded_file = request.FILES['file']
    source_lang = request.POST.get('source_lang', 'auto').strip()
    target_lang = request.POST.get('target_lang', '').strip()
    output_format = request.POST.get('output_format', 'txt').strip()

    if not target_lang:
        return JsonResponse({'error': 'Target language is required'}, status=400)

    # Validate language codes
    is_valid, err_msg = validate_language_codes(source_lang, target_lang, allow_source_auto=True)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    # Document type and size validations
    allowed_exts = ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png']
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_exts:
        return JsonResponse({'error': f'Unsupported file format {ext}. Allowed: PDF, DOCX, TXT, JPG, PNG'}, status=400)

    # Max size: 15MB
    max_size = 15 * 1024 * 1024
    if uploaded_file.size > max_size:
        return JsonResponse({'error': 'File size exceeds maximum limit of 15MB'}, status=400)

    # Save temporary file
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"doc_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(temp_dir, temp_filename)

    try:
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as write_err:
        logger.exception("Failed to write temporary file")
        return JsonResponse({'error': 'Failed to save file on server.'}, status=500)

    # Create translation history record
    history = DocumentTranslationHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        source_language=source_lang,
        target_language=target_lang,
        status='pending'
    )
    
    # Save original file to original_file FileField
    from django.core.files import File
    try:
        with open(temp_path, 'rb') as f:
            history.original_file.save(os.path.basename(temp_path), File(f), save=True)
    except Exception as save_err:
        logger.exception(f"Failed to save original file to history model: {str(save_err)}")

    # Check if Celery is active and running
    celery_active = False
    try:
        from project.celery import app as celery_app
        inspect = celery_app.control.inspect(timeout=0.15)
        pings = inspect.ping() if inspect else None
        celery_active = bool(pings)
    except Exception as e:
        logger.warning(f"Could not connect to Celery broker or ping workers: {str(e)}")
        celery_active = False

    if celery_active:
        try:
            from app.tasks import process_document_translation
            task = process_document_translation.delay(history.id, temp_path, output_format)
            return JsonResponse({
                'task_id': task.id,
                'history_id': history.id,
                'status': 'QUEUED'
            })
        except Exception as task_err:
            logger.warning(f"Failed to queue task asynchronously: {str(task_err)}. Falling back to sync.")
            celery_active = False

    # Synchronous Fallback if Celery is down/inactive
    task_id = str(uuid.uuid4())
    try:
        from app.tasks import process_document_translation
        sync_result = process_document_translation(history.id, temp_path, output_format)
        cache.set(f"sync_task_{task_id}", sync_result, timeout=600)
        return JsonResponse({
            'task_id': task_id,
            'history_id': history.id,
            'status': 'QUEUED'
        })
    except Exception as sync_err:
        logger.exception("Synchronous document translation failed")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        # Mark history as failed
        history.status = 'failure'
        history.error_message = str(sync_err)
        history.save()
        return JsonResponse({'error': f'Failed to process document: {str(sync_err)}'}, status=500)

@require_POST
def upload_voice_api(request):
    """
    POST API to upload or record voice audio for translation.
    Rate limits to 10 uploads per minute.
    Returns Celery task ID.
    """
    # Ensure OpenAI API key is configured
    if not getattr(settings, 'OPENAI_API_KEY', None):
        return JsonResponse({'error': 'OpenAI API client is not configured. Please set OPENAI_API_KEY.'}, status=500)

    # Rate limiting
    ip = get_client_ip(request)
    limit_key = f"rate_limit_upload_voice_{ip}"
    count = cache.get(limit_key, 0)
    if count >= 10:
        return JsonResponse({'error': 'Too many voice uploads. Please wait a minute.'}, status=429)
    cache.set(limit_key, count + 1, timeout=60)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No audio file uploaded'}, status=400)

    uploaded_file = request.FILES['file']
    target_lang = request.POST.get('target_lang', 'es').strip()

    # Validate language codes
    is_valid, err_msg = validate_language_codes('auto', target_lang, allow_source_auto=True)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    # Audio type and size validations
    allowed_exts = ['.wav', '.mp3', '.m4a', '.webm', '.ogg', '.caf']
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if not ext:
        content_type = getattr(uploaded_file, 'content_type', '') or ''
        if 'webm' in content_type:
            ext = '.webm'
        elif 'ogg' in content_type or 'opus' in content_type:
            ext = '.ogg'
        elif 'wav' in content_type:
            ext = '.wav'
        elif 'mp3' in content_type or 'mpeg' in content_type:
            ext = '.mp3'
        elif 'm4a' in content_type or 'mp4' in content_type:
            ext = '.m4a'
        elif 'caf' in content_type:
            ext = '.caf'
        else:
            # Fallback default
            ext = '.wav'
    if ext not in allowed_exts:
        return JsonResponse({'error': f'Unsupported audio format {ext}'}, status=400)

    # Max size: 10MB
    max_size = 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        return JsonResponse({'error': 'Audio file size exceeds maximum limit of 10MB'}, status=400)

    # Save temporary file
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"voice_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(temp_dir, temp_filename)

    try:
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as write_err:
        logger.exception("Failed to write temporary audio file")
        return JsonResponse({'error': 'Failed to save audio on server.'}, status=500)

    # Check if Celery is active and running
    celery_active = False
    try:
        from project.celery import app as celery_app
        # Short timeout (150ms) to prevent requests from blocking
        inspect = celery_app.control.inspect(timeout=0.15)
        pings = inspect.ping() if inspect else None
        celery_active = bool(pings)
    except Exception as e:
        logger.warning(f"Could not connect to Celery broker or ping workers: {str(e)}")
        celery_active = False

    user_id = request.user.id if request.user.is_authenticated else None

    if celery_active:
        try:
            from app.tasks import process_voice_translation
            task = process_voice_translation.delay(temp_path, target_lang, user_id=user_id)
            return JsonResponse({
                'task_id': task.id,
                'status': 'QUEUED'
            })
        except Exception as task_err:
            logger.warning(f"Failed to queue voice task asynchronously: {str(task_err)}. Falling back to sync.")
            celery_active = False

    # Synchronous Fallback if Celery is down/inactive
    task_id = str(uuid.uuid4())
    try:
        from app.tasks import process_voice_translation
        sync_result = process_voice_translation(temp_path, target_lang, user_id=user_id)
        cache.set(f"sync_task_{task_id}", sync_result, timeout=600)
        return JsonResponse({
            'task_id': task_id,
            'status': 'QUEUED'
        })
    except Exception as sync_err:
        logger.exception("Synchronous voice translation failed")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return JsonResponse({'error': f'Failed to process voice: {str(sync_err)}'}, status=500)

@require_GET
def task_status_api(request, task_id):
    """
    GET API to check status of a translation task.
    """
    task_id = task_id.strip()
    if not task_id:
        return JsonResponse({'error': 'Task ID is required'}, status=400)

    # 1. First check Django cache for synchronous fallback task results
    sync_result = cache.get(f"sync_task_{task_id}")
    if sync_result is not None:
        if sync_result.get('status') == 'SUCCESS':
            return JsonResponse({
                'status': 'SUCCESS',
                'result': sync_result
            })
        else:
            return JsonResponse({
                'status': 'FAILURE',
                'error': sync_result.get('error', 'An error occurred during task execution.')
            })

    # 2. Otherwise, check Celery AsyncResult
    try:
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return JsonResponse({
                'status': 'PENDING',
                'progress': 'Waiting in task queue...'
            })
        elif result.state == 'PROGRESS':
            info = result.info or {}
            status_msg = info.get('status', 'Processing data...')
            return JsonResponse({
                'status': 'PROGRESS',
                'progress': status_msg
            })
        elif result.state == 'SUCCESS':
            # Store in cache so subsequent checks are instantaneous
            cache.set(f"sync_task_{task_id}", result.result, timeout=600)
            return JsonResponse({
                'status': 'SUCCESS',
                'result': result.result
            })
        elif result.state == 'FAILURE':
            error_msg = str(result.result) or 'An error occurred during task execution.'
            return JsonResponse({
                'status': 'FAILURE',
                'error': error_msg
            })
        else:
            return JsonResponse({
                'status': result.state,
                'progress': 'Task state updated'
            })
    except Exception as e:
        logger.warning(f"Could not connect to Celery to fetch status: {str(e)}")
        # Check cache one last time
        sync_result = cache.get(f"sync_task_{task_id}")
        if sync_result:
            if sync_result.get('status') == 'SUCCESS':
                return JsonResponse({
                    'status': 'SUCCESS',
                    'result': sync_result
                })
            else:
                return JsonResponse({
                    'status': 'FAILURE',
                    'error': sync_result.get('error', 'An error occurred during task execution.')
                })
        return JsonResponse({
            'status': 'FAILURE',
            'error': f"Failed to check task status: Celery broker is currently offline."
        })

# =====================================================================
# CUSTOM ADMIN DASHBOARD VIEWS
# =====================================================================
from django.contrib.admin.views.decorators import staff_member_required

def dashboard_login(request):
    """Custom Login View for staff members to access the Admin Dashboard."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard_home')
        
    if request.method == 'POST':
        username_val = request.POST.get('username', '').strip()
        password_val = request.POST.get('password', '')
        
        if not username_val or not password_val:
            messages.error(request, "Please fill in all credentials.")
        else:
            # Query by email first just in case they used their email address
            user_obj = User.objects.filter(email=username_val).first()
            username = user_obj.username if user_obj else username_val
            
            user = authenticate(request, username=username, password=password_val)
            if user is not None:
                if user.is_staff:
                    login(request, user)
                    messages.success(request, "Logged in to Admin Console successfully.")
                    return redirect('dashboard_home')
                else:
                    messages.error(request, "Access denied. Only system staff can access the console.")
            else:
                messages.error(request, "Invalid username or password.")
                
    return render(request, 'dashboard/login.html')

@staff_member_required(login_url='dashboard_login')
def dashboard_logout(request):
    """Logs the staff member out of the Admin Console."""
    logout(request)
    messages.success(request, "Logged out of Admin Console.")
    return redirect('dashboard_login')

@staff_member_required(login_url='dashboard_login')
def dashboard_home(request):
    """Admin Dashboard Homepage presenting aggregated count stats and recent entries."""
    total_rev = PaymentTransaction.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0.00
    active_subs = UserSubscription.objects.filter(status='active').count()
    pending_txns = PaymentTransaction.objects.filter(status='pending').count()
    
    context = {
        'total_users': User.objects.count(),
        'total_blogs': Blog.objects.count(),
        'published_blogs': Blog.objects.filter(is_published=True).count(),
        'total_videos': YoutubeVideo.objects.count(),
        'published_videos': YoutubeVideo.objects.filter(is_published=True).count(),
        'total_messages': Contact.objects.count(),
        'unread_messages': Contact.objects.filter(is_read=False).count(),
        
        # Financial / Premium Metrics
        'total_revenue': total_rev,
        'active_subscriptions': active_subs,
        'pending_transactions': pending_txns,
        
        'latest_users': User.objects.order_by('-date_joined')[:5],
        'latest_blogs': Blog.objects.order_by('-created_date')[:5],
        'latest_videos': YoutubeVideo.objects.order_by('-created_date')[:5],
        'latest_messages': Contact.objects.order_by('-created_date')[:5],
    }
    return render(request, 'dashboard/home.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_blog_list(request):
    """Lists all blogs in the admin table, with search and pagination features."""
    blogs_list = Blog.objects.all()
    
    q = request.GET.get('q', '').strip()
    if q:
        blogs_list = blogs_list.filter(
            Q(title__icontains=q) | 
            Q(category__icontains=q) | 
            Q(author__icontains=q)
        )
        
    paginator = Paginator(blogs_list, 10) # 10 blogs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': q,
    }
    return render(request, 'dashboard/blog_list.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_blog_add(request):
    """Creates a new Blog entry via the dashboard."""
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            # Default author if blank
            if not blog.author:
                blog.author = request.user.first_name or request.user.username
            blog.save()
            messages.success(request, f"Blog '{blog.title}' created successfully!")
            return redirect('dashboard_blog_list')
        else:
            messages.error(request, "Failed to create blog. Please check your inputs.")
    else:
        form = BlogForm()
        
    context = {
        'form': form,
        'action': 'Add',
    }
    return render(request, 'dashboard/blog_form.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_blog_edit(request, pk):
    """Updates an existing Blog entry."""
    blog = get_object_or_404(Blog, pk=pk)
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, f"Blog '{blog.title}' updated successfully!")
            return redirect('dashboard_blog_list')
        else:
            messages.error(request, "Failed to update blog. Please check your inputs.")
    else:
        form = BlogForm(instance=blog)
        
    context = {
        'form': form,
        'action': 'Edit',
        'blog': blog,
    }
    return render(request, 'dashboard/blog_form.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_blog_delete(request, pk):
    """Deletes a Blog entry from the DB (requires POST request)."""
    if request.method == 'POST':
        blog = get_object_or_404(Blog, pk=pk)
        title = blog.title
        blog.delete()
        messages.success(request, f"Blog '{title}' deleted successfully.")
    return redirect('dashboard_blog_list')

@staff_member_required(login_url='dashboard_login')
def dashboard_video_list(request):
    """Lists all YouTube videos in the dashboard console."""
    videos_list = YoutubeVideo.objects.all()
    
    q = request.GET.get('q', '').strip()
    if q:
        videos_list = videos_list.filter(
            Q(title__icontains=q) | 
            Q(category__icontains=q)
        )
        
    paginator = Paginator(videos_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': q,
    }
    return render(request, 'dashboard/video_list.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_video_add(request):
    """Registers a new YouTube Video link."""
    if request.method == 'POST':
        form = YoutubeVideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
            messages.success(request, f"YouTube Video '{video.title}' registered successfully!")
            return redirect('dashboard_video_list')
        else:
            messages.error(request, "Failed to add video. Please check input parameters.")
    else:
        form = YoutubeVideoForm()
        
    context = {
        'form': form,
        'action': 'Add',
    }
    return render(request, 'dashboard/video_form.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_video_edit(request, pk):
    """Modifies details of an existing YouTube Video link."""
    video = get_object_or_404(YoutubeVideo, pk=pk)
    if request.method == 'POST':
        form = YoutubeVideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, f"YouTube Video '{video.title}' updated successfully!")
            return redirect('dashboard_video_list')
        else:
            messages.error(request, "Failed to update video details.")
    else:
        form = YoutubeVideoForm(instance=video)
        
    context = {
        'form': form,
        'action': 'Edit',
        'video': video,
    }
    return render(request, 'dashboard/video_form.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_video_delete(request, pk):
    """Deletes a YouTube Video registry (requires POST request)."""
    if request.method == 'POST':
        video = get_object_or_404(YoutubeVideo, pk=pk)
        title = video.title
        video.delete()
        messages.success(request, f"Video '{title}' deleted successfully.")
    return redirect('dashboard_video_list')

@staff_member_required(login_url='dashboard_login')
def dashboard_contact_list(request):
    """Displays contact message listings."""
    contacts_list = Contact.objects.all()
    
    paginator = Paginator(contacts_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'dashboard/contact_list.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_contact_view(request, pk):
    """Displays full details of a Contact Message and marks it as read."""
    msg = get_object_or_404(Contact, pk=pk)
    if not msg.is_read:
        msg.is_read = True
        msg.save()
        
    context = {
        'msg': msg,
    }
    return render(request, 'dashboard/contact_view.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_contact_mark_read(request, pk):
    """Marks a contact inquiry as read and redirects back to the list."""
    msg = get_object_or_404(Contact, pk=pk)
    msg.is_read = True
    msg.save()
    messages.success(request, f"Message from {msg.name} marked as read.")
    return redirect('dashboard_contact_list')

@staff_member_required(login_url='dashboard_login')
def dashboard_contact_mark_unread(request, pk):
    """Marks a contact inquiry as unread and redirects back to the list."""
    msg = get_object_or_404(Contact, pk=pk)
    msg.is_read = False
    msg.save()
    messages.success(request, f"Message from {msg.name} marked as unread.")
    return redirect('dashboard_contact_list')

@staff_member_required(login_url='dashboard_login')
def dashboard_user_list(request):
    """Displays system registered user listings."""
    users_list = User.objects.order_by('-date_joined')
    
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'dashboard/user_list.html', context)

# =====================================================================
# USER DASHBOARD VIEWS
# =====================================================================

@login_required(login_url='login')
def user_dashboard_home(request):
    """Authenticated user dashboard home showing stats and recent translations."""
    history = UserTranslationHistory.objects.filter(user=request.user).order_by('-created_date')
    recent_history = history[:5]
    
    total_translations = history.count()
    text_count = history.filter(tool_type='text').count()
    file_count = history.filter(tool_type='file').count()
    voice_count = history.filter(tool_type='voice').count()
    
    # Active subscription
    subscription = request.user.subscriptions.filter(status='active').first()
    
    # User payment history
    payment_history = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'recent_history': recent_history,
        'total_translations': total_translations,
        'text_count': text_count,
        'file_count': file_count,
        'voice_count': voice_count,
        'subscription': subscription,
        'payment_history': payment_history,
    }
    return render(request, 'user/home.html', context)

@login_required(login_url='login')
def user_profile(request):
    """Allows user to view/edit their profile and change password on one unified page."""
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile details updated successfully.")
                return redirect('user_profile')
            else:
                messages.error(request, "Failed to update profile details.")
        elif action == 'change_password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('user_profile')
            else:
                messages.error(request, "Failed to change password. Please correct the errors.")
                
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'user/profile.html', context)

@login_required(login_url='login')
def user_change_password(request):
    """Fallback redirect to the unified profile page."""
    return redirect('user_profile')

@login_required(login_url='login')
def user_tool_text(request):
    """Renders the text translation tool workspace."""
    from app.constants import LANGUAGES
    return render(request, 'user/tool_text.html', {'languages': LANGUAGES})

@login_required(login_url='login')
def user_tool_file(request):
    """Renders the document upload translation workspace."""
    from app.constants import LANGUAGES
    return render(request, 'user/tool_file.html', {'languages': LANGUAGES})

@login_required(login_url='login')
def user_tool_voice(request):
    """Renders the voice recording/audio upload translation workspace."""
    from app.constants import LANGUAGES
    return render(request, 'user/tool_voice.html', {'languages': LANGUAGES})

@login_required(login_url='login')
def user_history_list(request):
    """Lists all translation history records for the authenticated user."""
    history_list = UserTranslationHistory.objects.filter(user=request.user).order_by('-created_date')
    
    # Simple search
    q = request.GET.get('q', '').strip()
    if q:
        history_list = history_list.filter(
            Q(source_text__icontains=q) |
            Q(translated_text__icontains=q) |
            Q(file_name__icontains=q)
        )
        
    paginator = Paginator(history_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': q,
    }
    return render(request, 'user/history.html', context)

@login_required(login_url='login')
def user_logout(request):
    """Logs out user and redirects to public home page."""
    logout(request)
    messages.success(request, "Logged out of your user dashboard successfully.")
    return redirect('home')


# =====================================================================
# PHONEPE V2 PAYMENT GATEWAY INTEGRATION VIEWS
# =====================================================================

def populate_default_plans():
    """Ensure the three default pricing plans exist in the DB."""
    plans = [
        {
            'name': 'Basic Plan',
            'slug': 'basic',
            'price': 97.00,
            'plan_order': 1,
            'features': 'Text Translation Tool\n50,000 words per month\n30 supported languages\nStandard voice output\nBasic transliteration guides'
        },
        {
            'name': 'Pro Plan',
            'slug': 'pro',
            'price': 699.00,
            'plan_order': 2,
            'features': 'Everything in Basic\n500,000 words per month\n120+ supported languages\nHigh-fidelity voice synthesis\nAdvanced phonetic transliteration\nTranslate PDFs, DOCX (100 files/mo)'
        },
        {
            'name': 'Business Plan',
            'slug': 'business',
            'price': 1999.00,
            'plan_order': 3,
            'features': 'Everything in Pro\nUnlimited words translation\nAll supported languages\nDedicated GPU priority speed\nUnlimited document translation\nREST API keys (20 req/sec)\n24/7 Priority support channel'
        }
    ]
    for p in plans:
        obj, created = PricingPlan.objects.get_or_create(
            slug=p['slug'],
            defaults={
                'name': p['name'],
                'price': p['price'],
                'plan_order': p['plan_order'],
                'features': p['features'],
                'is_active': True,
                'billing_cycle': 'monthly'
            }
        )
        if not created:
            obj.plan_order = p['plan_order']
            obj.save()

def process_successful_payment(merchant_order_id, phonepe_order_id, phonepe_transaction_id, raw_response):
    try:
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(
                merchant_order_id=merchant_order_id
            )
            
            if payment_txn.status == 'success':
                return payment_txn
                
            payment_txn.status = 'success'
            payment_txn.phonepe_order_id = phonepe_order_id
            payment_txn.phonepe_transaction_id = phonepe_transaction_id
            payment_txn.callback_payload = json.dumps(raw_response)
            payment_txn.save()
            
            user = payment_txn.user
            plan = payment_txn.plan
            
            # Deactivate active subscriptions
            active_sub = UserSubscription.objects.filter(user=user, status='active').first()
            is_upgrade = False
            previous_plan = None
            
            if active_sub:
                previous_plan = active_sub.plan
                if plan != previous_plan:
                    is_upgrade = True
                UserSubscription.objects.filter(user=user, status='active').update(
                    status='expired',
                    end_date=timezone.now()
                )
            
            start_date = timezone.now()
            duration_days = 365 if plan.billing_cycle == 'yearly' else 30
            end_date = start_date + timedelta(days=duration_days)
            
            UserSubscription.objects.create(
                user=user,
                plan=plan,
                payment_transaction=payment_txn,
                status='active',
                start_date=start_date,
                end_date=end_date,
                is_upgrade=is_upgrade,
                previous_plan=previous_plan
            )
            
            logger.info(f"Subscription active for {user.username}: {plan.name} (Upgrade: {is_upgrade})")
            return payment_txn
    except PaymentTransaction.DoesNotExist:
        logger.error(f"Txn order {merchant_order_id} not found in DB.")
        return None
    except Exception as e:
        logger.exception(f"Error processing success: {str(e)}")
        return None

def process_failed_payment(merchant_order_id, phonepe_order_id, phonepe_transaction_id, raw_response, status='failed'):
    try:
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(
                merchant_order_id=merchant_order_id
            )
            if payment_txn.status == 'pending':
                payment_txn.status = status
                payment_txn.phonepe_order_id = phonepe_order_id
                payment_txn.phonepe_transaction_id = phonepe_transaction_id
                payment_txn.callback_payload = json.dumps(raw_response)
                payment_txn.save()
                return payment_txn
    except PaymentTransaction.DoesNotExist:
        pass
    return None

def pricing_select(request, plan_slug):
    """Handles guest redirects and authenticated user redirection to checkout with validations."""
    populate_default_plans()
    plan = get_object_or_404(PricingPlan, slug=plan_slug, is_active=True)
    
    if not request.user.is_authenticated:
        request.session['selected_plan_slug'] = plan.slug
        checkout_url = reverse('checkout', kwargs={'plan_slug': plan.slug})
        return redirect(f"{reverse('login')}?next={checkout_url}")
        
    active_sub = UserSubscription.objects.filter(user=request.user, status='active').first()
    if active_sub and active_sub.plan:
        if active_sub.plan.slug == plan.slug:
            messages.warning(request, "You have already chosen this plan.")
            return redirect('pricing')
        
        if plan.plan_order < active_sub.plan.plan_order:
            if not getattr(settings, 'ALLOW_DOWNGRADE', False):
                messages.error(request, "Downgrading to a lower plan is not allowed.")
                return redirect('pricing')
        
    return redirect('checkout', plan_slug=plan.slug)

@login_required(login_url='login')
def checkout(request, plan_slug):
    """Renders the checkout review page with validations."""
    populate_default_plans()
    plan = get_object_or_404(PricingPlan, slug=plan_slug, is_active=True)
    
    active_sub = UserSubscription.objects.filter(user=request.user, status='active').first()
    if active_sub and active_sub.plan:
        if active_sub.plan.slug == plan.slug:
            messages.warning(request, "You have already chosen this plan.")
            return redirect('pricing')
        
        if plan.plan_order < active_sub.plan.plan_order:
            if not getattr(settings, 'ALLOW_DOWNGRADE', False):
                messages.error(request, "Downgrading to a lower plan is not allowed.")
                return redirect('pricing')
                
    return render(request, 'checkout.html', {'plan': plan})

@login_required(login_url='login')
@require_POST
def payment_initiate(request, plan_slug):
    """Initiates PhonePe payment session using V2 SDK and redirects user with validations."""
    populate_default_plans()
    plan = get_object_or_404(PricingPlan, slug=plan_slug, is_active=True)
    
    active_sub = UserSubscription.objects.filter(user=request.user, status='active').first()
    if active_sub and active_sub.plan:
        if active_sub.plan.slug == plan.slug:
            messages.warning(request, "You have already chosen this plan.")
            return redirect('pricing')
            
        if plan.plan_order < active_sub.plan.plan_order:
            if not getattr(settings, 'ALLOW_DOWNGRADE', False):
                messages.error(request, "Downgrading to a lower plan is not allowed.")
                return redirect('pricing')
    
    # Generate unique merchant order ID (up to 35 chars)
    merchant_order_id = f"MO_{uuid.uuid4().hex[:12].upper()}_{int(timezone.now().timestamp())}"
    merchant_order_id = merchant_order_id[:35]
    
    # Create local transaction entry
    payment_txn = PaymentTransaction.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price,
        merchant_order_id=merchant_order_id,
        status='pending'
    )
    
    try:
        service = PhonePeService()
        # Call PhonePe pay request builder
        response = service.initiate_payment(
            merchant_order_id=merchant_order_id,
            amount_in_rupees=plan.price
        )
        
        # Save payload details in DB
        import dataclasses
        payment_txn.request_payload = json.dumps({
            "merchant_order_id": merchant_order_id,
            "amount": int(float(plan.price) * 100),
            "redirect_url": getattr(settings, 'PHONEPE_REDIRECT_URL', '')
        })
        payment_txn.response_payload = json.dumps(dataclasses.asdict(response))
        
        if response.order_id:
            payment_txn.phonepe_order_id = response.order_id
        payment_txn.save()
        
        if response.redirect_url:
            request.session['last_merchant_order_id'] = merchant_order_id
            return redirect(response.redirect_url)
        else:
            raise Exception("No redirect URL returned by PhonePe SDK.")
            
    except Exception as e:
        logger.exception(f"PhonePe SDK Pay initiation failed: {str(e)}")
        payment_txn.status = 'failed'
        payment_txn.save()
        messages.error(request, f"Failed to initiate payment session with PhonePe: {str(e)}")
        return redirect('checkout', plan_slug=plan.slug)

@login_required(login_url='login')
def payment_redirect(request):
    """Handle browser redirection callback from PhonePe."""
    merchant_order_id = request.POST.get('merchantOrderId') or request.GET.get('merchantOrderId') or \
                        request.POST.get('transactionId') or request.GET.get('transactionId') or \
                        request.session.get('last_merchant_order_id')
                      
    if not merchant_order_id:
        messages.error(request, "Unable to verify transaction details.")
        return redirect('pricing')
        
    try:
        service = PhonePeService()
        response = service.get_payment_status(merchant_order_id)
        
        state = getattr(response, 'state', 'FAILED')
        phonepe_order_id = getattr(response, 'order_id', '')
        
        # Find the latest payment transaction attempt detail from paymentDetails list
        phonepe_transaction_id = ''
        payment_details = getattr(response, 'payment_details', [])
        if payment_details and len(payment_details) > 0:
            phonepe_transaction_id = payment_details[0].transaction_id
            
        import dataclasses
        raw_response_dict = dataclasses.asdict(response)
        
        if state == 'COMPLETED':
            # Check if this is an upgrade prior to processing it
            txn = PaymentTransaction.objects.filter(merchant_order_id=merchant_order_id).first()
            plan = txn.plan if txn else None
            
            active_sub = UserSubscription.objects.filter(user=request.user, status='active').first()
            is_upgrade = active_sub is not None and plan is not None and active_sub.plan != plan
            
            process_successful_payment(
                merchant_order_id=merchant_order_id,
                phonepe_order_id=phonepe_order_id,
                phonepe_transaction_id=phonepe_transaction_id,
                raw_response=raw_response_dict
            )
            
            if is_upgrade:
                messages.success(request, f"Upgrade successful! Your subscription has been upgraded to {plan.name if plan else 'new plan'}.")
            else:
                messages.success(request, "Payment successful! Your subscription is now active.")
                
            if 'last_merchant_order_id' in request.session:
                del request.session['last_merchant_order_id']
            return redirect('payment_success')
        elif state == 'PENDING':
            if 'last_merchant_order_id' in request.session:
                del request.session['last_merchant_order_id']
            return redirect('payment_pending')
        else:
            process_failed_payment(
                merchant_order_id=merchant_order_id,
                phonepe_order_id=phonepe_order_id,
                phonepe_transaction_id=phonepe_transaction_id,
                raw_response=raw_response_dict
            )
            if 'last_merchant_order_id' in request.session:
                del request.session['last_merchant_order_id']
            return redirect('payment_failure')
            
    except Exception as e:
        logger.exception(f"Redirect processing failed: {str(e)}")
        messages.error(request, f"Error processing redirection: {str(e)}")
        return redirect('payment_failure')

@csrf_exempt
@require_POST
def payment_webhook(request):
    """Secure Server-to-Server callback hook verified by PhonePe SDK."""
    try:
        x_verify_header = request.headers.get('X-VERIFY')
        if not x_verify_header:
            return JsonResponse({"status": "error", "message": "Missing checksum"}, status=400)
            
        request_body_str = request.body.decode('utf-8')
        
        service = PhonePeService()
        callback_resp = service.validate_callback(x_verify_header, request_body_str)
        
        if not callback_resp or not callback_resp.payload:
            return JsonResponse({"status": "error", "message": "Validation failed"}, status=401)
            
        payload = callback_resp.payload
        merchant_order_id = payload.merchant_order_id
        phonepe_order_id = payload.order_id
        state = payload.state
        
        phonepe_transaction_id = ''
        payment_details = payload.payment_details
        if payment_details and len(payment_details) > 0:
            phonepe_transaction_id = payment_details[0].transaction_id
            
        import dataclasses
        raw_response_dict = dataclasses.asdict(payload)
        
        if state == 'COMPLETED':
            process_successful_payment(
                merchant_order_id=merchant_order_id,
                phonepe_order_id=phonepe_order_id,
                phonepe_transaction_id=phonepe_transaction_id,
                raw_response=raw_response_dict
            )
        else:
            process_failed_payment(
                merchant_order_id=merchant_order_id,
                phonepe_order_id=phonepe_order_id,
                phonepe_transaction_id=phonepe_transaction_id,
                raw_response=raw_response_dict
            )
            
        return JsonResponse({"status": "SUCCESS"})
    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='login')
def payment_success(request):
    """Displays payment success page."""
    return render(request, 'payment_success.html')

@login_required(login_url='login')
def payment_failure(request):
    """Displays payment failure page."""
    return render(request, 'payment_failure.html')

@login_required(login_url='login')
def payment_pending(request):
    """Displays payment pending page."""
    return render(request, 'payment_pending.html')

@staff_member_required(login_url='dashboard_login')
def dashboard_payment_list(request):
    """Lists all transactions in custom admin console."""
    txns = PaymentTransaction.objects.select_related('user', 'plan').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        txns = txns.filter(
            Q(merchant_order_id__icontains=q) |
            Q(phonepe_order_id__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q)
        )
        
    paginator = Paginator(txns, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': q,
    }
    return render(request, 'dashboard/payment_list.html', context)

@staff_member_required(login_url='dashboard_login')
def dashboard_subscription_list(request):
    """Lists active/expired subscriptions in custom admin console."""
    subs = UserSubscription.objects.select_related('user', 'plan', 'payment_transaction').order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        subs = subs.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(payment_transaction__merchant_order_id__icontains=q)
        )
        
    paginator = Paginator(subs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': q,
    }
    return render(request, 'dashboard/subscription_list.html', context)


@require_GET
def document_task_status(request, task_id):
    """
    GET API to check status of a document translation task.
    Queries cache or database history record.
    """
    task_id = task_id.strip()
    if not task_id:
        return JsonResponse({'error': 'Task ID is required'}, status=400)

    # 1. Check Django cache for synchronous fallback task results
    sync_result = cache.get(f"sync_task_{task_id}")
    if sync_result is not None:
        if sync_result.get('status') == 'SUCCESS':
            return JsonResponse({
                'status': 'SUCCESS',
                'result': sync_result
            })
        else:
            return JsonResponse({
                'status': 'FAILURE',
                'error': sync_result.get('error', 'An error occurred during task execution.')
            })

    # 2. Check Celery AsyncResult
    try:
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return JsonResponse({
                'status': 'PENDING',
                'progress': 'Waiting in task queue...'
            })
        elif result.state == 'PROGRESS':
            info = result.info or {}
            status_msg = info.get('status', 'Processing data...')
            return JsonResponse({
                'status': 'PROGRESS',
                'progress': status_msg
            })
        elif result.state == 'SUCCESS':
            cache.set(f"sync_task_{task_id}", result.result, timeout=600)
            return JsonResponse({
                'status': 'SUCCESS',
                'result': result.result
            })
        elif result.state == 'FAILURE':
            error_msg = str(result.result) or 'An error occurred during task execution.'
            return JsonResponse({
                'status': 'FAILURE',
                'error': error_msg
            })
        else:
            return JsonResponse({
                'status': result.state,
                'progress': 'Task processing state changed'
            })
    except Exception as e:
        logger.warning(f"Could not connect to Celery to fetch status: {str(e)}")
        # Check cache one last time
        sync_result = cache.get(f"sync_task_{task_id}")
        if sync_result:
            if sync_result.get('status') == 'SUCCESS':
                return JsonResponse({
                    'status': 'SUCCESS',
                    'result': sync_result
                })
            else:
                return JsonResponse({
                    'status': 'FAILURE',
                    'error': sync_result.get('error', 'Task failed.')
                })
        return JsonResponse({'status': 'PENDING', 'progress': 'Checking background task status...'})


def download_translated_file(request, id):
    """
    View that allows users to download the translated file securely.
    """
    import re
    from django.http import FileResponse, HttpResponseForbidden, Http404
    
    history = get_object_or_404(DocumentTranslationHistory, id=id)
    
    # Enforce authorization privacy checks
    if history.user:
        if history.user != request.user and not request.user.is_staff:
            return HttpResponseForbidden("You are not authorized to download this file.")
    else:
        # Anonymous translation download validation
        if not getattr(settings, 'ALLOW_ANONYMOUS_TRANSLATION', False):
            return HttpResponseForbidden("Anonymous downloads are not allowed.")
            
    if not history.download_file:
        raise Http404("Translated file is not available.")
        
    file_path = history.download_file.path
    if not os.path.exists(file_path):
        raise Http404("Translated file does not exist on disk.")
        
    # Build clean output name
    ext = os.path.splitext(file_path)[1]
    original_name = "translated_document" + ext
    if history.original_file:
        orig_base = os.path.splitext(os.path.basename(history.original_file.name))[0]
        # Strip internal temporary path prefixes if any
        orig_base = re.sub(r'^doc_[a-f0-9]+_', '', orig_base)
        original_name = f"{orig_base}_translated{ext}"
        
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=original_name)
    return response

