import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.core.cache import cache

from .models import AIConversation, AIMessage, ResumeEvaluation
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
    GET: Returns welcome message and session history.
    POST: Processes user query or quick action choice and returns AI response.
    """
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
            "history": messages
        })

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_text = (data.get('message') or data.get('action') or '').strip()

        if not user_text:
            return JsonResponse({"success": False, "error": "Please enter a question or choose a career path."}, status=400)

        conv = _get_or_create_conversation(request, 'career')

        # Save user message
        AIMessage.objects.create(conversation=conv, role='user', content=user_text)

        # Build history context (last 10 messages for token efficiency)
        messages_query = list(conv.messages.order_by('created_at')[:12])
        messages_history = [{'role': m.role, 'content': m.content} for m in messages_query]

        # Generate AI response
        ai_response_text = generate_career_response(messages_history)

        # Save assistant message
        AIMessage.objects.create(conversation=conv, role='assistant', content=ai_response_text)

        return JsonResponse({
            "success": True,
            "response": ai_response_text
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
    Extracts text, calls OpenAI, saves evaluation record, and returns JSON score dashboard data.
    """
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

        return JsonResponse({
            "success": True,
            "filename": filename,
            "target_role": target_role or "General Software Engineering",
            "evaluation": evaluation_result
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
    GET: Returns conversation history.
    POST: Processes general assistant queries and returns AI response.
    """
    if request.method == "GET":
        conv = _get_or_create_conversation(request, 'assistant')
        messages = list(conv.messages.values('role', 'content'))
        return JsonResponse({
            "success": True,
            "history": messages
        })

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

        return JsonResponse({
            "success": True,
            "response": ai_response_text
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
