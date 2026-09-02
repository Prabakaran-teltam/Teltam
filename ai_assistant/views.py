import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone

from .models import AIConversation, AIMessage, ResumeEvaluation
from app.models import UserSubscription
from .prompts import CAREER_WELCOME_MESSAGE
from .utils import extract_resume_text
from .services import (
    generate_career_response,
    evaluate_resume_with_ai,
    generate_assistant_response
)

logger = logging.getLogger(__name__)


def _get_or_create_session_key(request):
    """
    Ensures a valid session key exists for anonymous or authenticated requests.
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _check_chatbot_usage_and_subscription(request):
    """
    Checks chatbot limits based on subscription tier:
    - Guests / Unsubscribed Users: 3 free queries trial total limit.
    - Basic Plan Subscribers: 100 queries per day.
    - Pro Plan Subscribers: 500 queries per day.
    - Business Plan Subscribers: Unlimited queries.
    Returns (is_allowed, is_subscribed, usage_count, max_limit, remaining_inputs).
    """
    user = request.user if request.user.is_authenticated else None
    
    # 1. Active paid subscription check with tier limits
    if user:
        active_sub = UserSubscription.objects.filter(user=user, status='active').first()
        if active_sub and active_sub.plan:
            plan_slug = active_sub.plan.slug.lower()
            
            # Business Plan -> Unlimited queries
            if plan_slug == 'business':
                return True, True, 0, 'unlimited', 'unlimited'
            
            # Basic Plan (100 queries/day) & Pro Plan (500 queries/day)
            daily_limit = 500 if plan_slug == 'pro' else 100
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_msg_count = AIMessage.objects.filter(
                conversation__user=user, 
                role='user', 
                created_at__gte=today_start
            ).count()
            today_resume_count = ResumeEvaluation.objects.filter(
                user=user, 
                created_at__gte=today_start
            ).count()
            
            today_usage = today_msg_count + today_resume_count
            remaining = max(0, daily_limit - today_usage)
            is_allowed = (today_usage < daily_limit)
            
            return is_allowed, True, today_usage, daily_limit, remaining

    # 2. Count total AI query usage for unsubscribed user or guest session (3 free trial queries limit)
    session_key = _get_or_create_session_key(request)
    
    if user:
        msg_count = AIMessage.objects.filter(conversation__user=user, role='user').count()
        resume_count = ResumeEvaluation.objects.filter(user=user).count()
    else:
        msg_count = AIMessage.objects.filter(conversation__session_key=session_key, role='user').count()
        resume_count = ResumeEvaluation.objects.filter(session_key=session_key).count()

    total_usage = msg_count + resume_count
    max_limit = 3
    
    # Double check session fallback counter
    session_usage = request.session.get('chatbot_usage_count', 0)
    if session_usage > total_usage:
        total_usage = session_usage

    remaining = max(0, max_limit - total_usage)
    is_allowed = (total_usage < max_limit)
    return is_allowed, False, total_usage, max_limit, remaining


def _get_or_create_conversation(request, assistant_type='career'):
    """
    Retrieves or creates an AIConversation record for the current user/session.
    """
    session_key = _get_or_create_session_key(request)
    user = request.user if request.user.is_authenticated else None

    if user:
        conv = AIConversation.objects.filter(user=user, assistant_type=assistant_type).first()
        if not conv:
            conv = AIConversation.objects.create(
                user=user,
                session_key=session_key,
                assistant_type=assistant_type,
                title=f"{assistant_type.capitalize()} Chat"
            )
    else:
        conv = AIConversation.objects.filter(session_key=session_key, assistant_type=assistant_type, user__isnull=True).first()
        if not conv:
            conv = AIConversation.objects.create(
                session_key=session_key,
                assistant_type=assistant_type,
                title=f"{assistant_type.capitalize()} Chat"
            )

    return conv


@require_http_methods(["GET", "POST"])
def career_chat_api(request):
    """
    API endpoint for AI Career Advisor Chatbot.
    GET: Returns welcome message, session history, and remaining free query limit.
    POST: Processes user query or quick action choice and returns AI response.
    """
    is_allowed, is_subscribed, usage_count, max_limit, remaining = _check_chatbot_usage_and_subscription(request)

    if request.method == "GET":
        conv = _get_or_create_conversation(request, 'career')
        messages = list(conv.messages.values('role', 'content'))
        return JsonResponse({
            "success": True,
            "welcome_message": CAREER_WELCOME_MESSAGE,
            "quick_actions": [
                "Machine Learning Engineer",
                "Data Scientist",
                "AI Engineer",
                "Generative AI Engineer",
                "Data Engineer"
            ],
            "history": messages,
            "is_subscribed": is_subscribed,
            "usage_count": usage_count,
            "max_limit": max_limit,
            "remaining_inputs": remaining,
            "limit_reached": not is_allowed
        })

    if not is_allowed:
        err_text = f"You have reached your daily limit of {max_limit} AI queries for your plan. Upgrade your subscription for higher daily limits or unlimited access!" if is_subscribed else "You have reached your 3 free AI queries limit. Please choose a subscription plan to continue."
        return JsonResponse({
            "success": False,
            "limit_reached": True,
            "usage_count": usage_count,
            "max_limit": max_limit,
            "remaining_inputs": 0,
            "error": err_text,
            "redirect_url": "/pricing/"
        }, status=403)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_text = (data.get('message') or data.get('action') or '').strip()

        if not user_text:
            return JsonResponse({"success": False, "error": "Please enter a question or choose a career path."}, status=400)

        conv = _get_or_create_conversation(request, 'career')

        # Save user message
        AIMessage.objects.create(conversation=conv, role='user', content=user_text)

        # Build history context (last 12 messages for token efficiency)
        messages_query = list(conv.messages.order_by('created_at')[:12])
        messages_history = [{'role': m.role, 'content': m.content} for m in messages_query]

        # Generate AI response
        ai_response_text = generate_career_response(messages_history)

        # Save assistant message
        AIMessage.objects.create(conversation=conv, role='assistant', content=ai_response_text)

        # Increment session fallback counter if unsubscribed
        if not is_subscribed:
            request.session['chatbot_usage_count'] = usage_count + 1

        return JsonResponse({
            "success": True,
            "response": ai_response_text,
            "is_subscribed": is_subscribed,
            "remaining_inputs": max(0, remaining - 1) if not is_subscribed else 'unlimited'
        })

    except ValueError as ve:
        return JsonResponse({"success": False, "error": str(ve)}, status=400)
    except Exception as e:
        logger.exception("Error in career_chat_api")
        return JsonResponse({"success": False, "error": "Unable to process career advice request. Please try again."}, status=500)


@require_POST
def evaluate_resume_api(request):
    """
    API endpoint for Resume Evaluator.
    Accepts resume file (PDF/DOCX) and optional target_role.
    Enforces subscription tier daily query limits.
    """
    is_allowed, is_subscribed, usage_count, max_limit, remaining = _check_chatbot_usage_and_subscription(request)
    
    if not is_allowed:
        err_text = f"You have reached your daily limit of {max_limit} AI queries for your plan. Upgrade your subscription to evaluate more resumes!" if is_subscribed else "You have reached your 3 free AI queries limit. Please choose a subscription plan to evaluate resumes."
        return JsonResponse({
            "success": False,
            "limit_reached": True,
            "usage_count": usage_count,
            "max_limit": max_limit,
            "remaining_inputs": 0,
            "error": err_text,
            "redirect_url": "/pricing/"
        }, status=403)

    if 'file' not in request.FILES:
        return JsonResponse({"success": False, "error": "Please select a PDF or DOCX resume file to upload."}, status=400)

    uploaded_file = request.FILES['file']
    target_role = request.POST.get('target_role', '').strip()

    try:
        # Extract text from resume PDF or DOCX
        resume_text, filename = extract_resume_text(uploaded_file)

        # Evaluate resume with OpenAI
        evaluation_result = evaluate_resume_with_ai(resume_text, target_role)

        # Save evaluation record
        session_key = _get_or_create_session_key(request)
        user = request.user if request.user.is_authenticated else None

        ResumeEvaluation.objects.create(
            user=user,
            session_key=session_key,
            target_role=target_role,
            resume_filename=filename,
            score=evaluation_result.get('score', 0),
            result_json=evaluation_result
        )

        # Increment session fallback counter if unsubscribed
        if not is_subscribed:
            request.session['chatbot_usage_count'] = usage_count + 1

        return JsonResponse({
            "success": True,
            "filename": filename,
            "target_role": target_role or "General Software Engineering",
            "evaluation": evaluation_result,
            "is_subscribed": is_subscribed,
            "remaining_inputs": remaining
        })

    except ValueError as ve:
        return JsonResponse({"success": False, "error": str(ve)}, status=400)
    except Exception as e:
        logger.exception("Error in evaluate_resume_api")
        return JsonResponse({"success": False, "error": "An error occurred while analyzing your resume. Please try again."}, status=500)


@require_http_methods(["GET", "POST"])
def assistant_chat_api(request):
    """
    API endpoint for AI Personal Assistant.
    GET: Returns conversation history and usage limit status.
    POST: Processes general assistant queries and returns AI response.
    """
    is_allowed, is_subscribed, usage_count, max_limit, remaining = _check_chatbot_usage_and_subscription(request)

    if request.method == "GET":
        conv = _get_or_create_conversation(request, 'assistant')
        messages = list(conv.messages.values('role', 'content'))
        return JsonResponse({
            "success": True,
            "history": messages,
            "is_subscribed": is_subscribed,
            "usage_count": usage_count,
            "max_limit": max_limit,
            "remaining_inputs": remaining,
            "limit_reached": not is_allowed
        })

    if not is_allowed:
        err_text = f"You have reached your daily limit of {max_limit} AI queries for your plan. Upgrade your subscription for higher daily limits or unlimited access!" if is_subscribed else "You have reached your 3 free AI queries limit. Please choose a subscription plan to continue."
        return JsonResponse({
            "success": False,
            "limit_reached": True,
            "usage_count": usage_count,
            "max_limit": max_limit,
            "remaining_inputs": 0,
            "error": err_text,
            "redirect_url": "/pricing/"
        }, status=403)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_text = (data.get('message') or '').strip()

        if not user_text:
            return JsonResponse({"success": False, "error": "Please enter your message or question."}, status=400)

        conv = _get_or_create_conversation(request, 'assistant')

        # Save user message
        AIMessage.objects.create(conversation=conv, role='user', content=user_text)

        # Build history context
        messages_query = list(conv.messages.order_by('created_at')[:12])
        messages_history = [{'role': m.role, 'content': m.content} for m in messages_query]

        # Generate AI response
        ai_response_text = generate_assistant_response(messages_history)

        # Save assistant message
        AIMessage.objects.create(conversation=conv, role='assistant', content=ai_response_text)

        # Increment session fallback counter if unsubscribed
        if not is_subscribed:
            request.session['chatbot_usage_count'] = usage_count + 1

        return JsonResponse({
            "success": True,
            "response": ai_response_text,
            "is_subscribed": is_subscribed,
            "remaining_inputs": max(0, remaining - 1) if not is_subscribed else 'unlimited'
        })

    except ValueError as ve:
        return JsonResponse({"success": False, "error": str(ve)}, status=400)
    except Exception as e:
        logger.exception("Error in assistant_chat_api")
        return JsonResponse({"success": False, "error": "Unable to process assistant request. Please try again."}, status=500)


@require_POST
def clear_chat_api(request):
    """
    API endpoint to clear chat history for career or assistant chat.
    """
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        assistant_type = data.get('type', 'career')

        conv = _get_or_create_conversation(request, assistant_type)
        conv.messages.all().delete()

        return JsonResponse({
            "success": True,
            "message": "Conversation history cleared successfully."
        })
    except Exception as e:
        logger.exception("Error clearing chat")
        return JsonResponse({"success": False, "error": "Failed to clear chat history."}, status=500)
