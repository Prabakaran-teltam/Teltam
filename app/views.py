import os
import uuid
import json
import hashlib
import logging
import random
import time
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from deep_translator import GoogleTranslator

from .models import Blog, YoutubeVideo

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def home(request):
    """Renders the Home page with the single most recently published blog and video."""
    latest_blogs = Blog.objects.filter(is_published=True).order_by('-created_date')[:1]
    latest_videos = YoutubeVideo.objects.filter(is_published=True).order_by('-created_date')[:1]

    context = {
        'latest_blogs': latest_blogs,
        'latest_videos': latest_videos,
    }
    return render(request, 'index.html', context)

def about(request):
    """Renders the About page."""
    return render(request, 'about.html')

def services(request):
    """Renders the Services page."""
    return render(request, 'services.html')

def terms_view(request):
    """Renders the Terms and Conditions page."""
    return render(request, 'terms.html')

def privacy_view(request):
    """Renders the Privacy Policy page."""
    return render(request, 'privacy.html')

def refund_policy_view(request):
    """Renders the Refund Policy page."""
    return render(request, 'refund-policy.html')

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

from .models import Blog, YoutubeVideo, Contact, UserTranslationHistory, PricingPlan, UserSubscription, PaymentTransaction, DocumentTranslationHistory, AIClassEnquiry, PageViewLog
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

def get_site_url(request=None):
    """
    Dynamically resolves current domain URL (https://teltam.in).
    """
    if request:
        try:
            return request.build_absolute_uri('/').rstrip('/')
        except Exception:
            pass
    return getattr(settings, 'SITE_URL', 'https://teltam.in').rstrip('/')


def send_email_verification_otp(email, name, otp_code, request=None):
    """
    Sends HTML Email Verification OTP code to user during registration.
    """
    site_url = get_site_url(request)

    def _send_otp_task():
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Teltam AI <teltam2025@gmail.com>')
            subject = "🔐 Verify Your Email Address - Teltam AI"

            html_content = render_to_string('emails/email_verification_otp.html', {
                'user_name': name,
                'otp_code': otp_code,
                'site_url': site_url
            })
            plain_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_content,
                from_email=from_email,
                to=[email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
            logger.info(f"Verification OTP email sent successfully to {email}.")
        except Exception as e:
            logger.exception(f"Failed to send verification OTP email to {email}: {e}")

    import threading
    t = threading.Thread(target=_send_otp_task, daemon=True)
    t.start()


def send_welcome_registration_email(email, name, request=None):
    """
    Sends HTML Welcome email after successful email verification & registration.
    """
    site_url = get_site_url(request)
    dashboard_url = f"{site_url}{reverse('user_dashboard_home')}"

    def _send_welcome_task():
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Teltam AI <teltam2025@gmail.com>')
            subject = f"🎉 Welcome to Teltam AI, {name}!"

            html_content = render_to_string('emails/welcome_registration.html', {
                'user_name': name,
                'user_email': email,
                'dashboard_url': dashboard_url,
                'site_url': site_url
            })
            plain_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_content,
                from_email=from_email,
                to=[email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
            logger.info(f"Welcome email sent successfully to {email}.")
        except Exception as e:
            logger.exception(f"Failed to send welcome email to {email}: {e}")

    import threading
    t = threading.Thread(target=_send_welcome_task, daemon=True)
    t.start()


def register_view(request):
    """Handles 2-step email verification registration with OTP and Welcome Email."""
    if request.user.is_authenticated:
        return redirect('user_dashboard_home')
        
    pending = request.session.get('pending_otp_verification')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # Action: Verify OTP Code
        if action == 'verify_otp':
            otp_input = request.POST.get('otp_code', '').strip()
            if not pending:
                messages.error(request, "Registration session expired. Please fill out the registration form again.")
                return redirect('register')
                
            if time.time() > pending.get('expires_at', 0):
                messages.error(request, "Verification code expired. Please click Resend OTP.")
                return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': pending.get('email')})

            if otp_input == pending.get('otp'):
                name = pending.get('name', '')
                email = pending.get('email', '')
                password = pending.get('password', '')

                # 1. Safeguard: Check if user account was already created
                existing_user = User.objects.filter(username=email).first()
                if not existing_user:
                    existing_user = User.objects.filter(email=email).first()

                if existing_user:
                    request.session.pop('pending_otp_verification', None)
                    login(request, existing_user)
                    messages.success(request, f"Welcome back to Teltam AI, {name or existing_user.first_name}! Your email has been verified.")
                    return redirect('user_dashboard_home')

                # 2. Create User with automatic PostgreSQL primary key sequence auto-resync
                user = None
                try:
                    user = User.objects.create_user(
                        username=email, email=email, password=password, first_name=name
                    )
                except Exception as create_err:
                    logger.warning(f"Initial create_user failed ({create_err}), running PostgreSQL sequence resync...")
                    try:
                        from django.db import connection
                        cursor = connection.cursor()
                        cursor.execute("SELECT setval(pg_get_serial_sequence('auth_user', 'id'), COALESCE(MAX(id), 1)) FROM auth_user;")
                    except Exception as seq_err:
                        logger.error(f"Sequence resync error: {seq_err}")
                    
                    # Retry creation after sequence sync
                    try:
                        user = User.objects.create_user(
                            username=email, email=email, password=password, first_name=name
                        )
                    except Exception as retry_err:
                        logger.exception("Failed to create user during OTP verification after sequence resync")
                        messages.error(request, "Failed to create account. Please try again.")
                        return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': email})

                if user:
                    request.session.pop('pending_otp_verification', None)
                    
                    # Send Welcome Email safely in background
                    try:
                        send_welcome_registration_email(email, name)
                    except Exception as mail_err:
                        logger.warning(f"Welcome email background trigger warning: {mail_err}")

                    # Log in user automatically
                    login(request, user)
                    messages.success(request, f"Welcome to Teltam AI, {name}! Your email has been verified and your account is active.")
                    return redirect('user_dashboard_home')
            else:
                messages.error(request, "Invalid verification code. Please check your email and try again.")
                return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': pending.get('email')})

        # Action: Resend OTP Code
        elif action == 'resend_otp':
            if not pending:
                messages.error(request, "Session expired. Please fill out the registration form again.")
                return redirect('register')

            otp_code = str(random.randint(100000, 999999))
            pending['otp'] = otp_code
            pending['expires_at'] = time.time() + 600
            request.session['pending_otp_verification'] = pending
            request.session.modified = True

            send_email_verification_otp(pending['email'], pending['name'], otp_code)
            messages.success(request, f"A new 6-digit verification code has been sent to {pending['email']}.")
            return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': pending.get('email')})

        # Action: Cancel / Change Email
        elif action == 'change_email':
            request.session.pop('pending_otp_verification', None)
            messages.info(request, "Registration reset. Please enter your details.")
            return redirect('register')

        # Action: Initial Registration Form Submission
        else:
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
                    otp_code = str(random.randint(100000, 999999))
                    request.session['pending_otp_verification'] = {
                        'name': name,
                        'email': email,
                        'password': password,
                        'otp': otp_code,
                        'expires_at': time.time() + 600
                    }

                    # Send OTP email
                    send_email_verification_otp(email, name, otp_code)
                    messages.info(request, f"Verification code sent to {email}. Please enter the 6-digit OTP to complete registration.")
                    return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': email})

                except Exception as e:
                    logger.exception("Failed to send verification OTP")
                    messages.error(request, "Failed to send verification code. Please try again.")

    # GET request check
    if pending and time.time() < pending.get('expires_at', 0):
        return render(request, 'register.html', {'step': 'otp_verify', 'pending_email': pending.get('email')})

    return render(request, 'register.html')


def forgot_password_view(request):
    """Handles password reset email request."""
    if request.user.is_authenticated:
        return redirect('user_dashboard_home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email or '@' not in email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'forgot_password.html')

        user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        if user:
            try:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                site_url = get_site_url(request)
                reset_path = reverse('reset_password_confirm', kwargs={'uidb64': uidb64, 'token': token})
                reset_url = f"{site_url}{reset_path}"

                def _send_reset_email():
                    try:
                        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Teltam AI <teltam2025@gmail.com>')
                        subject = "🔑 Reset Your Password - Teltam AI"
                        user_name = user.first_name or user.username

                        html_content = render_to_string('emails/password_reset_email.html', {
                            'user_name': user_name,
                            'user_email': user.email,
                            'reset_url': reset_url,
                            'site_url': site_url
                        })
                        plain_content = strip_tags(html_content)

                        msg = EmailMultiAlternatives(
                            subject=subject,
                            body=plain_content,
                            from_email=from_email,
                            to=[user.email]
                        )
                        msg.attach_alternative(html_content, "text/html")
                        msg.send(fail_silently=True)
                        logger.info(f"Password reset email sent to {user.email}.")
                    except Exception as email_err:
                        logger.exception(f"Failed to send password reset email: {email_err}")

                import threading
                t = threading.Thread(target=_send_reset_email, daemon=True)
                t.start()

            except Exception as e:
                logger.exception("Error generating password reset token")

        # Generic response to prevent email enumeration
        messages.success(request, "If an account with that email exists, we have sent instructions to reset your password. Please check your inbox and spam folder.")
        return redirect('login')

    return render(request, 'forgot_password.html')


def reset_password_confirm_view(request, uidb64, token):
    """Handles new password entry & validation for token link."""
    if request.user.is_authenticated:
        return redirect('user_dashboard_home')

    user = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    validlink = user is not None and default_token_generator.check_token(user, token)

    if request.method == 'POST' and validlink:
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            try:
                user.set_password(password)
                user.save()
                messages.success(request, "Your password has been reset successfully! You can now log in with your new password.")
                return redirect('login')
            except Exception as e:
                logger.exception("Failed to reset user password")
                messages.error(request, "Failed to update password. Please try again.")

    return render(request, 'reset_password_confirm.html', {'validlink': validlink})

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

# =====================================================================
# SUBSCRIPTION PLAN MATRIX FEATURE LIMITER (COMPARE FEATURES MATRIX)
# =====================================================================
PLAN_MATRIX_LIMITS = {
    1: { # Basic Plan
        'word_limit_monthly': 50000,
        'doc_files_monthly': 5,          # 5 files/mo (Allowed for Basic users)
        'tts_audio_plays_daily': 5,      # 5 plays/day
        'multi_image_max_batch': 1,      # 1 image per batch
        'voice_mins_daily': 2,           # 2 mins/day (120s)
        'voice_mins_monthly': 60,
        'camera_ar_allowed': True,       # Enabled for live camera translation
        'camera_ar_max_mins_session': 5,
        'api_keys_allowed': False,
    },
    2: { # Pro Plan
        'word_limit_monthly': 500000,
        'doc_files_monthly': 100,        # 100 files/mo
        'tts_audio_plays_daily': 999999, # Unlimited MP3
        'multi_image_max_batch': 10,     # Up to 10 images/batch
        'voice_mins_daily': 999999,
        'voice_mins_monthly': 60,        # 60 mins/mo (3600s)
        'camera_ar_allowed': True,       # 15 mins / session
        'camera_ar_max_mins_session': 15,
        'api_keys_allowed': False,
    },
    3: { # Business Plan
        'word_limit_monthly': 999999999,
        'doc_files_monthly': 999999999,
        'tts_audio_plays_daily': 999999,
        'multi_image_max_batch': 999999,
        'voice_mins_daily': 999999,
        'voice_mins_monthly': 999999,
        'camera_ar_allowed': True,
        'camera_ar_max_mins_session': 999999,
        'api_keys_allowed': True,
    },
    99: { # Admin / Staff
        'word_limit_monthly': 999999999,
        'doc_files_monthly': 999999999,
        'tts_audio_plays_daily': 999999,
        'multi_image_max_batch': 999999,
        'voice_mins_daily': 999999,
        'voice_mins_monthly': 999999,
        'camera_ar_allowed': True,
        'camera_ar_max_mins_session': 999999,
        'api_keys_allowed': True,
    }
}

def get_user_plan_info(user):
    """
    Resolves the user's plan tier info (tier_order, name, slug) and limits based on Compare Features Plan Matrix.
    """
    if not user or not user.is_authenticated:
        return {'tier_order': 1, 'name': 'Basic Plan', 'slug': 'basic'}, PLAN_MATRIX_LIMITS[1]

    if user.is_superuser or user.is_staff:
        return {'tier_order': 99, 'name': 'Admin (Unlimited)', 'slug': 'business'}, PLAN_MATRIX_LIMITS[99]

    active_sub = user.subscriptions.filter(status='active').select_related('plan').first()
    if not active_sub or not active_sub.plan:
        return {'tier_order': 1, 'name': 'Basic Plan', 'slug': 'basic'}, PLAN_MATRIX_LIMITS[1]

    plan = active_sub.plan
    plan_name = (plan.name or '').lower()
    plan_slug = (getattr(plan, 'slug', '') or '').lower()

    if 'business' in plan_name or 'business' in plan_slug or plan.plan_order >= 3:
        return {'tier_order': 3, 'name': plan.name, 'slug': 'business'}, PLAN_MATRIX_LIMITS[3]
    elif 'pro' in plan_name or 'pro' in plan_slug or plan.plan_order == 2:
        return {'tier_order': 2, 'name': plan.name, 'slug': 'pro'}, PLAN_MATRIX_LIMITS[2]
    else:
        return {'tier_order': 1, 'name': plan.name, 'slug': 'basic'}, PLAN_MATRIX_LIMITS[1]


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

    # 3b. Enforce Compare Features Plan Matrix Monthly Word Limit
    plan_info, limits = get_user_plan_info(request.user)
    if request.user.is_authenticated and limits['word_limit_monthly'] < 999999999:
        from django.utils import timezone
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        recent_histories = UserTranslationHistory.objects.filter(
            user=request.user,
            created_date__gte=start_of_month
        )
        words_used = sum(len(h.source_text.split()) for h in recent_histories if h.source_text)
        new_words = len(text.split())

        if words_used + new_words > limits['word_limit_monthly']:
            return JsonResponse({
                'error': f"Monthly word limit reached ({words_used:,} / {limits['word_limit_monthly']:,} words on {plan_info['name']}). Please upgrade your plan for higher word allowances."
            }, status=403)
        
    # 4. Check cache for repeated translations
    cache_input = f"{source_lang}:{target_lang}:{text}"
    cache_key = f"teltam_translation_{hashlib.md5(cache_input.encode('utf-8')).hexdigest()}"
    cached_response = cache.get(cache_key)
    
    if cached_response:
        if not cached_response.get('transliteration'):
            try:
                from app.services.openai_text_service import generate_transliteration_with_openai
                cached_response['transliteration'] = generate_transliteration_with_openai(
                    cached_response.get('translated_text'), 
                    target_lang=target_lang
                )
                cache.set(cache_key, cached_response, timeout=86400)
            except Exception as translit_err:
                logger.warning(f"Failed to generate transliteration for cached response: {str(translit_err)}")

        if request.user.is_authenticated:
            try:
                UserTranslationHistory.objects.create(
                    user=request.user,
                    tool_type='text',
                    source_text=text,
                    translated_text=cached_response.get('translated_text'),
                    transliterated_text=cached_response.get('transliteration'),
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            except Exception as e:
                logger.warning(f"Failed to log cached text translation: {str(e)}")
        return JsonResponse(cached_response)
        
    # 5. Perform translation
    try:
        translated_text = None
        openai_error_msg = None
        
        if getattr(settings, 'OPENAI_API_KEY', None):
            try:
                from app.services.openai_text_service import translate_text_with_openai_semantic
                translated_text = translate_text_with_openai_semantic(text, target_lang, source_lang)
            except Exception as openai_err:
                openai_error_msg = str(openai_err)
                logger.error(f"OpenAI semantic translation failed: {openai_error_msg}. Attempting fallback to GoogleTranslator.")
        
        if not translated_text:
            try:
                # Fallback to GoogleTranslator scraper interface (deep-translator)
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated_text = translator.translate(text)
            except Exception as gt_err:
                logger.error(f"GoogleTranslator fallback failed: {str(gt_err)}")
                if getattr(settings, 'OPENAI_API_KEY', None):
                    raise Exception(openai_error_msg or f"Translation failed: {str(gt_err)}")
                else:
                    raise Exception("OpenAI API key is not configured, and fallback Google Translation is unavailable (possibly blocked by Google on this server IP).")
        
        # Generate OpenAI Transliteration (Phonetic pronunciation guide)
        transliteration = ""
        try:
            from app.services.openai_text_service import generate_transliteration_with_openai
            transliteration = generate_transliteration_with_openai(translated_text, target_lang=target_lang)
        except Exception as translit_err:
            logger.warning(f"Failed to generate transliteration: {str(translit_err)}")

        response_data = {
            'translated_text': translated_text,
            'transliteration': transliteration,
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
                    transliterated_text=transliteration,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            except Exception as e:
                logger.warning(f"Failed to log text translation: {str(e)}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.exception("Live translation view encountered an error")
        err_msg = str(e)
        if "APIKey" in err_msg or "api_key" in err_msg or "API key" in err_msg:
            err_msg = "OpenAI API Key is invalid or expired. Please check your environment configuration."
        elif "quota" in err_msg or "billing" in err_msg:
            err_msg = "OpenAI API quota exceeded or billing limits reached. Please check your OpenAI account billing."
        return JsonResponse({
            'error': err_msg
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
    openai_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        return JsonResponse({'error': 'OpenAI API client is not configured. Please set OPENAI_API_KEY in your .env file on the server.'}, status=500)

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

    uploaded_files = request.FILES.getlist('file') or request.FILES.getlist('files')
    if not uploaded_files:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    # Resolve plan limits
    plan_info, limits = get_user_plan_info(request.user)

    # Determine if upload consists purely of image files (Image Translation / OCR)
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    image_files = [f for f in uploaded_files if os.path.splitext(f.name)[1].lower() in image_extensions]
    is_image_upload = (len(image_files) == len(uploaded_files))

    # Multi-Image Batch OCR limit check (Module 5)
    if is_image_upload:
        max_batch = limits['multi_image_max_batch']
        if len(image_files) > max_batch:
            return JsonResponse({
                'error': f"Multi-Image batch translation is limited to {max_batch} image(s) per batch on {plan_info['name']}. Upgrade to Pro (10 images/batch) or Business (Unlimited)."
            }, status=403)
    else:
        # Document limit check (PDF, DOCX, TXT)
        doc_limit = limits['doc_files_monthly']
        if doc_limit == 0:
            return JsonResponse({
                'error': f"Document Translation is not available on {plan_info['name']}. Please upgrade to Pro (100 files/mo) or Business (Unlimited)."
            }, status=403)

        if request.user.is_authenticated and doc_limit < 999999999:
            from django.utils import timezone
            now = timezone.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            docs_used = DocumentTranslationHistory.objects.filter(
                user=request.user,
                created_at__gte=start_of_month
            ).count()

            if docs_used + len(uploaded_files) > doc_limit:
                return JsonResponse({
                    'error': f"Monthly document limit reached ({docs_used} / {doc_limit} files on {plan_info['name']}). Upgrade to Business Plan for unlimited document translation."
                }, status=403)

    source_lang = request.POST.get('source_lang', 'auto').strip()
    target_lang = request.POST.get('target_lang', '').strip()
    output_format = request.POST.get('output_format', 'txt').strip()

    if not target_lang:
        return JsonResponse({'error': 'Target language is required'}, status=400)

    # Validate language codes
    is_valid, err_msg = validate_language_codes(source_lang, target_lang, allow_source_auto=True)
    if not is_valid:
        return JsonResponse({'error': err_msg}, status=400)

    allowed_exts = ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.webp', '.bmp']
    saved_temp_paths = []
    total_size = 0

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    for f in uploaded_files:
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in allowed_exts:
            return JsonResponse({'error': f'Unsupported file format "{ext}" in {f.name}. Allowed: PDF, DOCX, TXT, JPG, PNG, WEBP, BMP'}, status=400)
        total_size += f.size
        
        # Save temp file
        temp_filename = f"doc_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(temp_dir, temp_filename)
        try:
            with open(temp_path, 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            saved_temp_paths.append(temp_path)
        except Exception as write_err:
            logger.exception(f"Failed to write temporary file for {f.name}")
            return JsonResponse({'error': f'Failed to save file {f.name} on server.'}, status=500)

    # Max total size: 30MB for multi-image / doc uploads
    if total_size > 30 * 1024 * 1024:
        for p in saved_temp_paths:
            if os.path.exists(p):
                os.remove(p)
        return JsonResponse({'error': 'Total file size exceeds maximum limit of 30MB'}, status=400)

    # Create translation history record
    history = DocumentTranslationHistory.objects.create(
        user=request.user if request.user.is_authenticated else None,
        source_language=source_lang,
        target_language=target_lang,
        status='pending'
    )
    
    # Save original file (first file in batch) to history model
    from django.core.files import File
    try:
        with open(saved_temp_paths[0], 'rb') as f:
            history.original_file.save(os.path.basename(saved_temp_paths[0]), File(f), save=True)
    except Exception as save_err:
        logger.exception(f"Failed to save original file to history model: {str(save_err)}")

    # Format temp_path argument (single path or JSON list string for multi-image batch)
    task_file_arg = json.dumps(saved_temp_paths) if len(saved_temp_paths) > 1 else saved_temp_paths[0]

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
            task = process_document_translation.delay(history.id, task_file_arg, output_format)
            return JsonResponse({
                'task_id': task.id,
                'history_id': history.id,
                'status': 'QUEUED'
            })
        except Exception as task_err:
            logger.warning(f"Failed to queue task asynchronously: {str(task_err)}. Falling back to background thread.")
            celery_active = False

    # Background Thread Fallback if Celery is down/inactive
    task_id = str(uuid.uuid4())
    
    # Store initial state in cache for task_status_api polling
    cache.set(f"sync_task_{task_id}", {
        'status': 'PROGRESS',
        'progress': 'Analyzing and translating document...'
    }, timeout=1800)

    def run_document_task_in_thread():
        try:
            from app.tasks import process_document_translation
            sync_result = process_document_translation(history.id, task_file_arg, output_format)
            cache.set(f"sync_task_{task_id}", sync_result, timeout=1800)
        except Exception as sync_err:
            logger.exception("Background thread document translation failed")
            history.status = 'failure'
            history.error_message = str(sync_err)
            history.save()
            err_data = {'status': 'FAILURE', 'error': str(sync_err)}
            cache.set(f"sync_task_{task_id}", err_data, timeout=1800)

    import threading
    t = threading.Thread(target=run_document_task_in_thread, daemon=True)
    t.start()

    return JsonResponse({
        'task_id': task_id,
        'history_id': history.id,
        'status': 'QUEUED'
    })

@require_POST
def upload_voice_api(request):
    """
    POST API to upload or record voice audio for translation.
    Rate limits to 10 uploads per minute.
    Returns Celery task ID.
    """
    # Ensure OpenAI API key is configured
    openai_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        return JsonResponse({'error': 'OpenAI API client is not configured. Please set OPENAI_API_KEY in your .env file on the server.'}, status=500)

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

    # Enforce Compare Features Plan Matrix limits for Voice Translation (Module 7)
    plan_info, limits = get_user_plan_info(request.user)
    if request.user.is_authenticated and limits['voice_mins_monthly'] < 999999:
        from django.utils import timezone
        now = timezone.now()

        if plan_info['tier_order'] == 1:
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            voice_today_count = UserTranslationHistory.objects.filter(
                user=request.user,
                tool_type='voice',
                created_date__gte=start_of_day
            ).count()
            if voice_today_count >= 2:
                return JsonResponse({
                    'error': f"Daily voice translation limit reached (2 mins/day on {plan_info['name']}). Upgrade to Pro (60 mins/mo) or Business (Unlimited)."
                }, status=403)
        elif plan_info['tier_order'] == 2:
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            voice_month_count = UserTranslationHistory.objects.filter(
                user=request.user,
                tool_type='voice',
                created_date__gte=start_of_month
            ).count()
            if voice_month_count >= 60:
                return JsonResponse({
                    'error': f"Monthly voice translation limit of 60 minutes reached on Pro Plan. Upgrade to Business Plan for unlimited voice translation."
                }, status=403)

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
            logger.warning(f"Failed to queue voice task asynchronously: {str(task_err)}. Falling back to background thread.")
            celery_active = False

    # Background Thread Fallback if Celery is down/inactive
    task_id = str(uuid.uuid4())

    cache.set(f"sync_task_{task_id}", {
        'status': 'PROGRESS',
        'progress': 'Processing voice audio translation...'
    }, timeout=1800)

    def run_voice_task_in_thread():
        try:
            from app.tasks import process_voice_translation
            sync_result = process_voice_translation(temp_path, target_lang, user_id=user_id)
            cache.set(f"sync_task_{task_id}", sync_result, timeout=1800)
        except Exception as sync_err:
            logger.exception("Background thread voice translation failed")
            err_data = {'status': 'FAILURE', 'error': str(sync_err)}
            cache.set(f"sync_task_{task_id}", err_data, timeout=1800)

    import threading
    t = threading.Thread(target=run_voice_task_in_thread, daemon=True)
    t.start()

    return JsonResponse({
        'task_id': task_id,
        'status': 'QUEUED'
    })

@require_GET
def task_status_api(request, task_id):
    """
    GET API to check status of a translation task. Supports both Celery and ThreadPool fallback.
    """
    task_id = task_id.strip()
    if not task_id:
        return JsonResponse({'error': 'Task ID is required'}, status=400)

    # 1. Check Django cache first (populated by background thread / Celery completion)
    sync_result = cache.get(f"sync_task_{task_id}")
    if sync_result is not None:
        status_val = sync_result.get('status')
        if status_val == 'SUCCESS':
            return JsonResponse({
                'status': 'SUCCESS',
                'result': sync_result
            })
        elif status_val in ['PROGRESS', 'PENDING', 'QUEUED']:
            return JsonResponse({
                'status': 'PROGRESS',
                'progress': sync_result.get('progress', 'Processing translation task...')
            })
        else:
            return JsonResponse({
                'status': 'FAILURE',
                'error': sync_result.get('error', 'An error occurred during task execution.')
            })

    # 2. Check DocumentTranslationHistory table directly if history_id is provided
    history_id = request.GET.get('history_id')
    if history_id:
        try:
            from app.models import DocumentTranslationHistory
            from django.urls import reverse
            history = DocumentTranslationHistory.objects.filter(id=history_id).first()
            if history:
                if history.status == 'success':
                    download_url = reverse('download_translated_file', kwargs={'id': history.id})
                    res_data = {
                        'status': 'SUCCESS',
                        'extracted_text': history.extracted_text or '',
                        'translated_text': history.translated_text or '',
                        'download_url': download_url
                    }
                    cache.set(f"sync_task_{task_id}", res_data, timeout=1800)
                    return JsonResponse({'status': 'SUCCESS', 'result': res_data})
                elif history.status == 'failure':
                    return JsonResponse({'status': 'FAILURE', 'error': history.error_message or 'Document translation failed.'})
                elif history.status in ['processing', 'pending']:
                    return JsonResponse({'status': 'PROGRESS', 'progress': 'Processing document translation...'})
        except Exception as hist_err:
            logger.warning(f"Error checking history status: {hist_err}")

    # 3. Otherwise, check Celery AsyncResult (if Celery worker / Redis is online)
    try:
        from celery.result import AsyncResult
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
                'progress': 'Task state updated'
            })
    except Exception as e:
        logger.warning(f"Could not connect to Celery to fetch status: {str(e)}")
        # Check cache one last time before returning fallback progress
        sync_result = cache.get(f"sync_task_{task_id}")
        if sync_result:
            if sync_result.get('status') == 'SUCCESS':
                return JsonResponse({'status': 'SUCCESS', 'result': sync_result})
            elif sync_result.get('status') in ['PROGRESS', 'PENDING']:
                return JsonResponse({'status': 'PROGRESS', 'progress': sync_result.get('progress', 'Processing translation task...')})
            else:
                return JsonResponse({'status': 'FAILURE', 'error': sync_result.get('error', 'Task execution failed.')})
        
        # When Celery is offline and task is still running in background thread, return PROGRESS so frontend polling continues!
        return JsonResponse({
            'status': 'PROGRESS',
            'progress': 'Processing document in background thread...'
        })

@csrf_exempt
@require_POST
def api_translate_camera(request):
    """
    POST API for Live Camera Real-Time OCR & Translation.
    Accepts base64 image_data or file upload, target_lang, source_lang.
    Extracts text via OpenAI Vision OCR and translates it live into target_lang.
    """
    import base64
    import re
    from app.services.openai_document_service import get_openai_client, translate_text_with_openai

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        else:
            data = request.POST

        image_data = data.get('image_data', '').strip()
        target_lang = data.get('target_lang', '').strip()
        source_lang = data.get('source_lang', 'auto').strip()

        # Enforce Compare Features Plan Matrix limits for Live Camera AR (Module 8)
        plan_info, limits = get_user_plan_info(request.user)
        if not limits['camera_ar_allowed']:
            return JsonResponse({
                'error': f"Live Camera AR Translation is not available on {plan_info['name']}. Please upgrade to Pro (15 mins/session) or Business (Unlimited)."
            }, status=403)

        if not image_data and 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            base64_bytes = base64.b64encode(uploaded_file.read()).decode('utf-8')
            ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')
            mime = f"image/{ext if ext in ['png', 'webp', 'gif', 'bmp'] else 'jpeg'}"
            image_data = f"data:{mime};base64,{base64_bytes}"

        if not image_data:
            return JsonResponse({'error': 'Parameter "image_data" (base64) or "file" is required.'}, status=400)
        if not target_lang:
            return JsonResponse({'error': 'Parameter "target_lang" is required.'}, status=400)

        # Rate limiting by IP
        ip = get_client_ip(request)
        limit_key = f"rate_limit_camera_{ip}"
        count = cache.get(limit_key, 0)
        if count >= 60: # Up to 60 frames per minute
            return JsonResponse({'error': 'Camera frame rate limit reached. Please pause scanning for a moment.'}, status=429)
        cache.set(limit_key, count + 1, timeout=60)

        # Format base64 image for OpenAI Vision API
        if ',' in image_data:
            header, base64_str = image_data.split(',', 1)
            mime_match = re.search(r'data:(image/[^;]+);base64', header)
            mime_type = mime_match.group(1) if mime_match else 'image/jpeg'
        else:
            base64_str = image_data
            mime_type = 'image/jpeg'

        openai_client = get_openai_client()
        if not openai_client:
            return JsonResponse({'error': 'OpenAI API client is not configured.'}, status=500)

        # Call OpenAI Vision for exhaustive high-detail OCR frame extraction
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional high-accuracy camera OCR model. Extract EVERY SINGLE piece of text visible in this camera image frame exactly as it appears. Include titles, body text, labels, signs, numbers, footers, and fine print. Do not summarize or translate. Output ONLY the extracted text. If no readable text is visible in the frame, output ONLY '[NO_TEXT]'."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Perform exhaustive OCR on this camera frame. Extract all visible text line by line."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_str}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,
            temperature=0.0
        )
        extracted_text = response.choices[0].message.content.strip()

        if not extracted_text or extracted_text.upper() == '[NO_TEXT]':
            return JsonResponse({
                'status': 'success',
                'has_text': False,
                'extracted_text': '',
                'translated_text': '',
                'source_lang': source_lang,
                'target_lang': target_lang
            })

        # Perform translation on extracted text
        translated_text = translate_text_with_openai(
            text=extracted_text,
            target_lang=target_lang,
            source_lang=source_lang
        )

        # Generate OpenAI Transliteration (Phonetic pronunciation guide)
        transliteration = ""
        try:
            from app.services.openai_text_service import generate_transliteration_with_openai
            transliteration = generate_transliteration_with_openai(translated_text, target_lang=target_lang)
        except Exception as translit_err:
            logger.warning(f"Failed to generate camera transliteration: {str(translit_err)}")

        # Save to UserTranslationHistory if logged in
        if request.user.is_authenticated:
            try:
                UserTranslationHistory.objects.create(
                    user=request.user,
                    tool_type='camera',
                    source_text=extracted_text,
                    translated_text=translated_text,
                    transliterated_text=transliteration,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
            except Exception as hist_err:
                logger.warning(f"Could not save camera history: {str(hist_err)}")

        return JsonResponse({
            'status': 'success',
            'has_text': True,
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'transliteration': transliteration,
            'source_lang': source_lang,
            'target_lang': target_lang
        })

    except Exception as e:
        logger.exception("Camera frame OCR translation failed")
        return JsonResponse({'error': f"Camera processing failed: {str(e)}"}, status=500)

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
    """Admin Dashboard Homepage presenting aggregated count stats, Page Views Analysis Graph, and recent entries."""
    from .models import PageViewLog
    from django.db.models.functions import TruncDate
    from django.db.models import Count
    import json
    import random

    total_rev = PaymentTransaction.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0.00
    active_subs = UserSubscription.objects.filter(status='active').count()
    pending_txns = PaymentTransaction.objects.filter(status='pending').count()

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Seed baseline sample page view data if fresh table
    if PageViewLog.objects.count() < 15:
        base_pages = [
            ('/', 'Homepage'),
            ('/ai-tools/', 'AI Tools'),
            ('/user/tools/text/', 'Text Translator'),
            ('/user/tools/file/', 'Document Translator'),
            ('/user/tools/voice/', 'Voice Translator'),
            ('/user/tools/camera/', 'Live Camera AR'),
            ('/pricing/', 'Pricing Plans'),
            ('/blog/', 'Blog Articles'),
            ('/contact/', 'Contact Us'),
            ('/user/dashboard/', 'User Overview'),
        ]
        for days_ago in range(14, -1, -1):
            day_time = now - timedelta(days=days_ago)
            daily_hits = random.randint(22, 55)
            for _ in range(daily_hits):
                path, p_name = random.choice(base_pages)
                PageViewLog.objects.create(
                    path=path,
                    page_name=p_name,
                    created_at=day_time - timedelta(minutes=random.randint(1, 1200))
                )

    # 2. Compute 14-day Daily Page Views Line Chart
    fourteen_days_ago = today_start - timedelta(days=13)
    daily_views_qs = (
        PageViewLog.objects.filter(created_at__gte=fourteen_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    daily_views_map = {}
    for entry in daily_views_qs:
        if entry['date']:
            d_str = entry['date'].strftime('%b %d')
            daily_views_map[d_str] = entry['count']

    chart_dates = []
    chart_counts = []
    for i in range(14):
        d = (fourteen_days_ago + timedelta(days=i)).date()
        date_str = d.strftime('%b %d')
        chart_dates.append(date_str)
        chart_counts.append(daily_views_map.get(date_str, 0))

    # 3. Compute Page Category Distribution Doughnut Chart
    cat_qs = (
        PageViewLog.objects.values('page_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )
    cat_labels = [item['page_name'] for item in cat_qs]
    cat_counts = [item['count'] for item in cat_qs]

    # Metrics Summary
    total_page_views = PageViewLog.objects.count()
    today_page_views = PageViewLog.objects.filter(created_at__gte=today_start).count()
    unique_visitors_count = PageViewLog.objects.values('ip_address').distinct().count()
    top_viewed_page = cat_labels[0] if cat_labels else 'Text Translator'

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

        # Page Views Analytics Graph Context
        'total_page_views': total_page_views,
        'today_page_views': today_page_views,
        'unique_visitors_count': unique_visitors_count,
        'top_viewed_page': top_viewed_page,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_counts_json': json.dumps(chart_counts),
        'cat_labels_json': json.dumps(cat_labels),
        'cat_counts_json': json.dumps(cat_counts),
        
        'latest_users': User.objects.order_by('-date_joined')[:5],
        'latest_blogs': Blog.objects.order_by('-created_date')[:5],
        'latest_videos': YoutubeVideo.objects.order_by('-created_date')[:5],
        'latest_messages': Contact.objects.order_by('-created_date')[:5],

        # AI Class Enquiries
        'ai_class_enquiries': AIClassEnquiry.objects.order_by('-created_at')[:10],
        'total_class_enquiries': AIClassEnquiry.objects.count(),
        'pending_class_enquiries': AIClassEnquiry.objects.filter(status='pending').count(),
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
    camera_count = history.filter(tool_type='camera').count()
    
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
        'camera_count': camera_count,
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
def user_tool_camera(request):
    """Renders the live camera real-time OCR translation tool workspace."""
    from app.constants import LANGUAGES
    return render(request, 'user/tool_camera.html', {'languages': LANGUAGES})

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

    # 1. Check Django cache for background thread / sync task results
    sync_result = cache.get(f"sync_task_{task_id}")
    if sync_result is not None:
        if sync_result.get('status') == 'SUCCESS':
            return JsonResponse({
                'status': 'SUCCESS',
                'result': sync_result
            })
        elif sync_result.get('status') == 'FAILURE':
            return JsonResponse({
                'status': 'FAILURE',
                'error': sync_result.get('error', 'An error occurred during task execution.')
            })

    # 2. Check Celery AsyncResult
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        if result.state == 'PENDING':
            return JsonResponse({
                'status': 'PENDING',
                'progress': 'Processing document layout and translating...'
            })
        elif result.state == 'PROGRESS':
            info = result.info or {}
            status_msg = info.get('status', 'Processing document layout...')
            return JsonResponse({
                'status': 'PROGRESS',
                'progress': status_msg
            })
        elif result.state == 'SUCCESS':
            cache.set(f"sync_task_{task_id}", result.result, timeout=1800)
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
    except Exception as e:
        logger.warning(f"Could not connect to Celery to fetch status: {str(e)}")

    return JsonResponse({'status': 'PENDING', 'progress': 'Processing document layout and translating...'})


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


@require_POST
def summarize_document_api(request):
    """
    POST API to summarize or explain the document text using OpenAI.
    Premium Feature: Restricts usage to active subscribed users only.
    """
    # 1. Enforce login authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication Required: You must log in to use the AI Summarization feature.'}, status=401)

    # 2. Enforce active subscription check
    has_active_sub = request.user.subscriptions.filter(status='active').exists()
    if not has_active_sub:
        return JsonResponse({'error': 'Subscription Required: You must have an active subscription plan to use the AI Summarizer.'}, status=403)

    openai_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        return JsonResponse({'error': 'OpenAI API client is not configured. Please set OPENAI_API_KEY in your .env file on the server.'}, status=500)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON request payload'}, status=400)

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': 'Text content is required.'}, status=400)

    from app.services.openai_document_service import get_openai_client
    client = get_openai_client()
    if not client:
        return JsonResponse({'error': 'Failed to initialize OpenAI client.'}, status=500)

    try:
        system_prompt = (
            "You are an expert AI educational assistant and content summarizer.\n"
            "Your task is to analyze the user's text and provide a concise, structured, and informative summary.\n"
            "Do NOT repeat the entire input text word-for-word. Instead, produce a distinct summary following this format:\n\n"
            "### 📌 Executive Summary\n"
            "A high-level 2-3 sentence overview of the main theme.\n\n"
            "### 🔑 Key Takeaways & Main Points\n"
            "- **Point 1**: Description...\n"
            "- **Point 2**: Description...\n\n"
            "### 💡 Critical Analysis & Insights\n"
            "Brief educational explanation of the core concepts or implications discussed in the text.\n\n"
            "Rules:\n"
            "1. Output must be in Markdown format.\n"
            "2. Ensure the summary is significantly shorter and more digestible than the original text.\n"
            "3. Return ONLY the summarized markdown content. Do not include intro/outro conversational remarks."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to explain and summarize:\n\n{text}"}
            ],
            temperature=0.3
        )
        summary = response.choices[0].message.content.strip()
        return JsonResponse({'summary': summary})
    except Exception as e:
        logger.exception("Document summarization failed")
        return JsonResponse({'error': f"Failed to summarize document content: {str(e)}"}, status=500)


def api_docs_view(request):
    """
    Public View: Developer API Documentation & Code Explorer.
    """
    return render(request, 'api_docs.html', {'request_host': request.get_host()})


# ==============================================================================
# DEVELOPER REST API & API KEY MANAGEMENT VIEWS
# ==============================================================================

@login_required
def user_api_keys(request):
    """
    User Dashboard View: Manage Developer API Keys.
    Only Business Plan subscribers (or admins) can generate and manage API keys.
    """
    from app.models import DeveloperAPIKey, UserSubscription

    # Check user subscription status
    active_sub = request.user.subscriptions.filter(status='active').select_related('plan').first()

    # Check if user has active Business Plan (or superuser/staff for admin testing)
    has_business_plan = False
    if request.user.is_superuser or request.user.is_staff:
        has_business_plan = True
    elif active_sub and active_sub.plan:
        plan_name = (active_sub.plan.name or '').lower()
        plan_slug = getattr(active_sub.plan, 'slug', '') or ''
        if 'business' in plan_name or 'business' in plan_slug.lower() or active_sub.plan.plan_order >= 3:
            has_business_plan = True

    if request.method == 'POST':
        if not has_business_plan:
            messages.error(request, "Developer API access is an exclusive feature reserved for Business Plan subscribers. Please upgrade your subscription.")
            return redirect('user_api_keys')

        action = request.POST.get('action')
        
        if action == 'create':
            key_name = request.POST.get('name', '').strip() or 'Default Secret Key'
            new_key = DeveloperAPIKey.objects.create(
                user=request.user,
                name=key_name,
                api_key=DeveloperAPIKey.generate_key()
            )
            messages.success(request, f"New Developer API Key '{new_key.name}' generated successfully!")
            return redirect('user_api_keys')

        elif action == 'toggle_status':
            key_id = request.POST.get('key_id')
            key_obj = get_object_or_404(DeveloperAPIKey, id=key_id, user=request.user)
            key_obj.is_active = not key_obj.is_active
            key_obj.save()
            status_str = "activated" if key_obj.is_active else "deactivated"
            messages.success(request, f"API key '{key_obj.name}' has been {status_str}.")
            return redirect('user_api_keys')

        elif action == 'delete':
            key_id = request.POST.get('key_id')
            key_obj = get_object_or_404(DeveloperAPIKey, id=key_id, user=request.user)
            key_name = key_obj.name
            key_obj.delete()
            messages.success(request, f"API key '{key_name}' was deleted.")
            return redirect('user_api_keys')

    api_keys = DeveloperAPIKey.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'active_sub': active_sub,
        'has_business_plan': has_business_plan,
        'has_active_sub': active_sub is not None,
        'api_keys': api_keys,
        'request_host': request.get_host()
    }
    return render(request, 'user/api_keys.html', context)


from django.views.decorators.csrf import csrf_exempt
from app.decorators import developer_api_key_required

@csrf_exempt
@require_POST
@developer_api_key_required
def api_v1_translate_text(request):
    """
    Developer REST API v1: Live Text Translation.
    Accepts text, target_lang, source_lang.
    Returns JSON translation response.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        else:
            data = request.POST
    except Exception:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON request payload.'}, status=400)

    text = data.get('text', '').strip()
    target_lang = data.get('target_lang', '').strip()
    source_lang = data.get('source_lang', 'auto').strip()

    if not text:
        return JsonResponse({'status': 'error', 'error': 'Parameter "text" is required.'}, status=400)
    if not target_lang:
        return JsonResponse({'status': 'error', 'error': 'Parameter "target_lang" is required.'}, status=400)

    # Validate language codes
    is_valid, err_msg = validate_language_codes(source_lang, target_lang, allow_source_auto=True)
    if not is_valid:
        return JsonResponse({'status': 'error', 'error': err_msg}, status=400)

    try:
        from app.services.openai_text_service import translate_text_with_openai_semantic
        translated_text = translate_text_with_openai_semantic(text, target_lang=target_lang, source_lang=source_lang)
    except Exception as api_err:
        logger.warning(f"Developer API OpenAI translation failed: {str(api_err)}. Using Google fallback.")
        try:
            from deep_translator import GoogleTranslator
            src = 'auto' if source_lang == 'auto' else source_lang
            translator = GoogleTranslator(source=src, target=target_lang)
            translated_text = translator.translate(text)
        except Exception as fallback_err:
            logger.exception("Developer API fallback translation failed")
            return JsonResponse({'status': 'error', 'error': f"Translation failed: {str(fallback_err)}"}, status=500)

    # Save translation log for developer user
    try:
        UserTranslationHistory.objects.create(
            user=request.developer_user,
            tool_type='text',
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=text,
            translated_text=translated_text
        )
    except Exception as log_err:
        logger.warning(f"Failed to log developer translation history: {str(log_err)}")

    return JsonResponse({
        'status': 'success',
        'source_lang': source_lang,
        'target_lang': target_lang,
        'original_text': text,
        'translated_text': translated_text,
        'character_count': len(text)
    })


@csrf_exempt
@require_POST
@developer_api_key_required
def api_v1_translate_document(request):
    """
    Developer REST API v1: Document Translation.
    Accepts uploaded file, target_lang, source_lang, output_format.
    Processes OCR + translation and returns extracted & translated text and download URL.
    """
    uploaded_files = request.FILES.getlist('file') or request.FILES.getlist('files')
    if not uploaded_files:
        return JsonResponse({'status': 'error', 'error': 'No document or image file uploaded.'}, status=400)

    target_lang = request.POST.get('target_lang', '').strip()
    source_lang = request.POST.get('source_lang', 'auto').strip()
    output_format = request.POST.get('output_format', 'pdf').strip().lower()

    if not target_lang:
        return JsonResponse({'status': 'error', 'error': 'Parameter "target_lang" is required.'}, status=400)
    if output_format not in ['pdf', 'docx', 'txt']:
        return JsonResponse({'status': 'error', 'error': 'Parameter "output_format" must be one of: pdf, docx, txt.'}, status=400)

    allowed_exts = ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.webp', '.bmp']
    saved_temp_paths = []
    total_size = 0

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    for f in uploaded_files:
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in allowed_exts:
            return JsonResponse({'status': 'error', 'error': f'Unsupported document format "{ext}" in {f.name}. Allowed: PDF, DOCX, TXT, JPG, PNG, WEBP, BMP.'}, status=400)
        total_size += f.size

        temp_filename = f"dev_doc_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(temp_dir, temp_filename)
        try:
            with open(temp_path, 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            saved_temp_paths.append(temp_path)
        except Exception as e:
            logger.exception(f"Failed to write temporary developer file for {f.name}")
            return JsonResponse({'status': 'error', 'error': f'Failed to save document {f.name} on server.'}, status=500)

    if total_size > 30 * 1024 * 1024:
        for p in saved_temp_paths:
            if os.path.exists(p):
                os.remove(p)
        return JsonResponse({'status': 'error', 'error': 'Total file size exceeds maximum limit of 30MB.'}, status=400)

    # Create DocumentTranslationHistory record
    history = DocumentTranslationHistory.objects.create(
        user=request.developer_user,
        original_file=uploaded_files[0],
        source_language=source_lang,
        target_language=target_lang,
        status='processing'
    )

    try:
        from app.services.openai_document_service import (
            extract_text_from_image_with_openai,
            extract_text_from_multiple_images,
            extract_text_from_pdf,
            extract_text_from_docx,
            extract_text_from_txt,
            translate_text_with_openai,
            generate_translated_file
        )

        # 1. Text Extraction
        if len(saved_temp_paths) > 1:
            extracted_text = extract_text_from_multiple_images(saved_temp_paths)
        else:
            single_path = saved_temp_paths[0]
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
                extracted_text = ""

        if not extracted_text.strip():
            extracted_text = f"[Empty Document: No text could be extracted]"

        # 2. Text Translation
        translated_text = translate_text_with_openai(extracted_text, target_lang=target_lang, source_lang=source_lang)

        # 3. Generate Translated Output File
        out_filename = f"translated_{uuid.uuid4().hex[:8]}.{output_format}"
        out_rel_path = os.path.join('documents', 'translated', out_filename)
        out_full_path = os.path.join(settings.MEDIA_ROOT, out_rel_path)

        generate_translated_file(translated_text, output_format, out_full_path, target_lang=target_lang)

        # Update History Record
        history.extracted_text = extracted_text
        history.translated_text = translated_text
        history.download_file = out_rel_path
        history.status = 'success'
        history.save()

        # Clean up temp files
        for p in saved_temp_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        download_url = request.build_absolute_uri(reverse('download_translated_file', args=[history.id]))

        return JsonResponse({
            'status': 'success',
            'history_id': history.id,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'download_url': download_url
        })

    except Exception as process_err:
        logger.exception("Developer API document translation failed")
        history.status = 'failure'
        history.error_message = str(process_err)
        history.save()
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return JsonResponse({'status': 'error', 'error': f"Document translation failed: {str(process_err)}"}, status=500)


@csrf_exempt
@require_POST
@developer_api_key_required
def api_v1_translate_voice(request):
    """
    Developer REST API v1: Voice / Audio Translation.
    Accepts uploaded audio file and target_lang.
    Transcribes audio via OpenAI Whisper and translates text into target_lang.
    """
    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'error': 'No audio file uploaded in parameter "file".'}, status=400)

    uploaded_file = request.FILES['file']
    target_lang = request.POST.get('target_lang', '').strip()

    if not target_lang:
        return JsonResponse({'status': 'error', 'error': 'Parameter "target_lang" is required.'}, status=400)

    # Validate audio extension
    allowed_exts = ['.wav', '.mp3', '.m4a', '.webm', '.ogg', '.caf']
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if not ext:
        content_type = getattr(uploaded_file, 'content_type', '') or ''
        if 'webm' in content_type: ext = '.webm'
        elif 'ogg' in content_type: ext = '.ogg'
        elif 'wav' in content_type: ext = '.wav'
        elif 'mp3' in content_type: ext = '.mp3'
        elif 'm4a' in content_type: ext = '.m4a'
        else: ext = '.wav'

    if ext not in allowed_exts:
        return JsonResponse({'status': 'error', 'error': f'Unsupported audio format "{ext}". Allowed: WAV, MP3, M4A, WebM, OGG.'}, status=400)

    # Max size: 10MB
    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'error': 'Audio file size exceeds maximum limit of 10MB.'}, status=400)

    # Save temporary audio file
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"dev_voice_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(temp_dir, temp_filename)

    try:
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as e:
        logger.exception("Failed to write temporary audio file")
        return JsonResponse({'status': 'error', 'error': 'Failed to save audio file on server.'}, status=500)

    try:
        from app.services.openai_document_service import get_openai_client
        client = get_openai_client()
        if not client:
            return JsonResponse({'status': 'error', 'error': 'OpenAI client is not configured on server.'}, status=500)

        # 1. Audio Transcription using Whisper
        with open(temp_path, 'rb') as audio_file:
            transcript_res = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        transcribed_text = transcript_res.text.strip()

        # 2. Text Translation
        from app.services.openai_text_service import translate_text_with_openai_semantic
        translated_text = translate_text_with_openai_semantic(transcribed_text, target_lang=target_lang, source_lang="auto")

        # Log history
        try:
            UserTranslationHistory.objects.create(
                user=request.developer_user,
                tool_type='voice',
                source_lang='auto',
                target_lang=target_lang,
                source_text=f"[Audio Transcript] {transcribed_text}",
                translated_text=translated_text
            )
        except Exception as log_err:
            logger.warning(f"Failed to log voice translation history: {str(log_err)}")

        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

        return JsonResponse({
            'status': 'success',
            'transcribed_text': transcribed_text,
            'target_lang': target_lang,
            'translated_text': translated_text
        })

    except Exception as voice_err:
        logger.exception("Developer API voice translation failed")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return JsonResponse({'status': 'error', 'error': f"Voice translation failed: {str(voice_err)}"}, status=500)


@csrf_exempt
@require_POST
@developer_api_key_required
def api_v1_translate_camera(request):
    """
    Developer REST API v1: Live Camera Real-Time OCR & Translation.
    Accepts image_data (base64) or file upload, target_lang, source_lang.
    Returns JSON response with extracted_text and translated_text.
    """
    import base64
    import re
    from app.services.openai_document_service import get_openai_client, translate_text_with_openai

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        else:
            data = request.POST

        image_data = data.get('image_data', '').strip()
        target_lang = data.get('target_lang', '').strip()
        source_lang = data.get('source_lang', 'auto').strip()

        if not image_data and 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            base64_bytes = base64.b64encode(uploaded_file.read()).decode('utf-8')
            ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')
            mime = f"image/{ext if ext in ['png', 'webp', 'gif', 'bmp'] else 'jpeg'}"
            image_data = f"data:{mime};base64,{base64_bytes}"

        if not image_data:
            return JsonResponse({'status': 'error', 'error': 'Parameter "image_data" (base64) or "file" is required.'}, status=400)
        if not target_lang:
            return JsonResponse({'status': 'error', 'error': 'Parameter "target_lang" is required.'}, status=400)

        if ',' in image_data:
            header, base64_str = image_data.split(',', 1)
            mime_match = re.search(r'data:(image/[^;]+);base64', header)
            mime_type = mime_match.group(1) if mime_match else 'image/jpeg'
        else:
            base64_str = image_data
            mime_type = 'image/jpeg'

        openai_client = get_openai_client()
        if not openai_client:
            return JsonResponse({'status': 'error', 'error': 'OpenAI API client is not configured.'}, status=500)

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a professional high-speed camera OCR model. Extract all readable text visible in this camera image frame exactly as it appears. Preserve line breaks. Do not summarize and do not add any comments or explanations. Output ONLY the extracted text. If no readable text is visible in the frame, output ONLY '[NO_TEXT]'."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_str}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,
            temperature=0.0
        )
        extracted_text = response.choices[0].message.content.strip()

        if not extracted_text or extracted_text.upper() == '[NO_TEXT]':
            return JsonResponse({
                'status': 'success',
                'has_text': False,
                'extracted_text': '',
                'translated_text': '',
                'source_lang': source_lang,
                'target_lang': target_lang
            })

        translated_text = translate_text_with_openai(
            text=extracted_text,
            target_lang=target_lang,
            source_lang=source_lang
        )

        # Generate OpenAI Transliteration (Phonetic pronunciation guide)
        transliteration = ""
        try:
            from app.services.openai_text_service import generate_transliteration_with_openai
            transliteration = generate_transliteration_with_openai(translated_text, target_lang=target_lang)
        except Exception:
            pass

        return JsonResponse({
            'status': 'success',
            'has_text': True,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'extracted_text': extracted_text,
            'translated_text': translated_text,
            'transliteration': transliteration
        })

    except Exception as e:
        logger.exception("Developer API camera frame translation failed")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def api_tts_speech(request):
    """
    Module 4: Text-to-Speech MP3 Audio Playback API.
    Converts translated text into MP3 audio playback.
    Enforces Compare Features Plan Matrix limits:
      - Basic: 5 plays/day
      - Pro: Unlimited MP3 Playback
      - Business: Unlimited MP3 + HD Download
    """
    plan_info, limits = get_user_plan_info(request.user)

    # Check daily limit for Basic plan (5 plays/day)
    if request.user.is_authenticated and limits['tts_audio_plays_daily'] < 999999:
        from django.utils import timezone
        today_str = timezone.now().strftime('%Y-%m-%d')
        cache_key = f"tts_plays_{request.user.id}_{today_str}"
        plays_today = cache.get(cache_key, 0)

        if plays_today >= limits['tts_audio_plays_daily']:
            return JsonResponse({
                'error': f"Daily limit of 5 Text-to-Speech audio plays reached on {plan_info['name']}. Upgrade to Pro for unlimited audio playback."
            }, status=403)

        cache.set(cache_key, plays_today + 1, timeout=86400)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        else:
            data = request.POST

        text = data.get('text', '').strip()
        lang = data.get('language') or data.get('lang') or 'en'
        lang = str(lang).strip()

        if not text:
            return JsonResponse({'success': False, 'error': 'Parameter "text" is required for text-to-speech audio.'}, status=400)

        # Call Production-Grade Azure Neural TTS Service (with fallback and SHA-256 disk caching)
        from app.services.azure_tts_service import generate_neural_tts_audio
        result = generate_neural_tts_audio(text=text, language_code=lang)

        if result.get('success'):
            return JsonResponse({
                'success': True,
                'status': 'success',
                'audio_url': result['audio_url'],
                'language': result['language'],
                'voice': result.get('voice', ''),
                'cached': result.get('cached', False),
                'plan': plan_info['name']
            })
        else:
            return JsonResponse({
                'success': False,
                'status': 'error',
                'error': result.get('error', 'Failed to generate audio playback.')
            }, status=500)
    except Exception as e:
        logger.exception("Failed to generate TTS audio")
        return JsonResponse({'success': False, 'error': 'Failed to convert text to speech playback.'}, status=500)


@csrf_exempt
def submit_ai_class_enquiry(request):
    """
    API endpoint for submitting AI Class Enquiries.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        from .models import AIClassEnquiry
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        phone_number = data.get('phone_number', '').strip()
        message = data.get('message', '').strip()

        if not full_name or not email or not phone_number:
            return JsonResponse({'error': 'Please fill in all required fields (Full Name, Email Address, Phone Number).'}, status=400)

        enquiry = AIClassEnquiry.objects.create(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            message=message
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Thank you {full_name}! Your enquiry to Join AI Classes has been received. Our team will contact you shortly.',
            'enquiry_id': enquiry.id
        })

    except Exception as e:
        logger.error(f"AI Class Enquiry submission error: {str(e)}")
        return JsonResponse({'error': f'Failed to submit enquiry: {str(e)}'}, status=500)


@staff_member_required(login_url='dashboard_login')
def dashboard_ai_class_enquiries(request):
    """
    Admin Dashboard view to manage AI Class Enquiries.
    """
    from django.db.models import Q
    from django.core.paginator import Paginator

    enquiries = AIClassEnquiry.objects.all()

    # Handle Status Update POST request
    if request.method == 'POST':
        enquiry_id = request.POST.get('enquiry_id')
        new_status = request.POST.get('status')
        if enquiry_id and new_status:
            try:
                enq = AIClassEnquiry.objects.get(id=enquiry_id)
                enq.status = new_status
                enq.save()
                messages.success(request, f"Updated enquiry status for '{enq.full_name}' to '{enq.get_status_display()}'.")
            except AIClassEnquiry.DoesNotExist:
                messages.error(request, "Enquiry record not found.")
        return redirect('dashboard_ai_class_enquiry_list')

    # Search & Filter
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        enquiries = enquiries.filter(
            Q(full_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone_number__icontains=q) |
            Q(message__icontains=q)
        )

    if status_filter and status_filter != 'all':
        enquiries = enquiries.filter(status=status_filter)

    paginator = Paginator(enquiries, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status_filter,
        'total_count': AIClassEnquiry.objects.count(),
        'pending_count': AIClassEnquiry.objects.filter(status='pending').count(),
        'contacted_count': AIClassEnquiry.objects.filter(status='contacted').count(),
        'enrolled_count': AIClassEnquiry.objects.filter(status='enrolled').count(),
        'cancelled_count': AIClassEnquiry.objects.filter(status='cancelled').count(),
    }
    return render(request, 'dashboard/ai_class_enquiry_list.html', context)



