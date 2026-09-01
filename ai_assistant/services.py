import os
import json
import logging
from django.conf import settings
from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError
from .prompts import (
    CAREER_SYSTEM_PROMPT,
    RESUME_EVALUATOR_SYSTEM_PROMPT,
    ASSISTANT_SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)

# Cached OpenAI client
_openai_client = None

def get_openai_client():
    """
    Returns configured OpenAI client instance using settings.OPENAI_API_KEY.
    """
    global _openai_client
    api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY', '')
    if isinstance(api_key, str):
        api_key = api_key.strip().strip('"').strip("'")
    if api_key:
        if not _openai_client:
            _openai_client = OpenAI(api_key=api_key)
        return _openai_client
    return None


def generate_career_response(messages_history):
    """
    Generates Career Advisor response given conversation history list of dicts [{'role': 'user'/'assistant', 'content': '...'}].
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY.")

    formatted_messages = [{"role": "system", "content": CAREER_SYSTEM_PROMPT}]
    for msg in messages_history:
        role = msg.get('role')
        content = msg.get('content', '')
        if role in ['user', 'assistant'] and content:
            formatted_messages.append({"role": role, "content": content})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=formatted_messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        logger.error("OpenAI Rate Limit Exceeded in Career Chat")
        raise ValueError("OpenAI API rate limit exceeded. Please try again in a few moments.")
    except APIConnectionError:
        logger.error("OpenAI API Connection Error in Career Chat")
        raise ValueError("Network error connecting to OpenAI API. Please check server connectivity.")
    except APIStatusError as e:
        logger.error(f"OpenAI API Error ({e.status_code}): {e.message}")
        raise ValueError(f"OpenAI service returned an error ({e.status_code}). Please try again later.")
    except Exception as e:
        logger.exception("Unexpected error in generate_career_response")
        raise ValueError(f"Unable to process AI career request: {str(e)}")


def evaluate_resume_with_ai(resume_text, target_role=""):
    """
    Evaluates resume text using OpenAI gpt-4o-mini with json_object response format.
    Returns parsed dictionary matching structured evaluation schema.
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY.")

    user_prompt = f"Resume Content:\n\n{resume_text}\n\n"
    if target_role and target_role.strip():
        user_prompt += f"Target Job Role: {target_role.strip()}\n"
    else:
        user_prompt += "Target Job Role: General Software Engineering / Technology Professional\n"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": RESUME_EVALUATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )

        raw_json = response.choices[0].message.content.strip()
        data = json.loads(raw_json)

        # Sanitize score structure
        score = int(data.get('score', 75))
        score = max(0, min(100, score))

        breakdown = data.get('breakdown', {})
        sanitized_breakdown = {
            'structure': max(0, min(100, int(breakdown.get('structure', score)))),
            'skills': max(0, min(100, int(breakdown.get('skills', score)))),
            'experience': max(0, min(100, int(breakdown.get('experience', score)))),
            'projects': max(0, min(100, int(breakdown.get('projects', score)))),
            'keywords': max(0, min(100, int(breakdown.get('keywords', score)))),
            'content_quality': max(0, min(100, int(breakdown.get('content_quality', score))))
        }

        result = {
            "score": score,
            "breakdown": sanitized_breakdown,
            "summary": str(data.get('summary', 'Resume evaluated successfully.')),
            "strengths": data.get('strengths', []),
            "weaknesses": data.get('weaknesses', []),
            "existing_skills": data.get('existing_skills', []),
            "missing_skills": data.get('missing_skills', []),
            "recommendations": data.get('recommendations', [])
        }
        return result

    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to parse JSON response from OpenAI: {json_err}")
        raise ValueError("AI evaluation generated an invalid data format. Please try again.")
    except RateLimitError:
        logger.error("OpenAI Rate Limit Exceeded in Resume Evaluator")
        raise ValueError("OpenAI API rate limit exceeded. Please try again in a few moments.")
    except APIConnectionError:
        logger.error("OpenAI API Connection Error in Resume Evaluator")
        raise ValueError("Network error connecting to OpenAI API. Please check server connectivity.")
    except Exception as e:
        logger.exception("Unexpected error in evaluate_resume_with_ai")
        raise ValueError(f"Unable to evaluate resume: {str(e)}")


def generate_assistant_response(messages_history):
    """
    Generates AI Personal Assistant response given conversation history list of dicts.
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY.")

    formatted_messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]
    for msg in messages_history:
        role = msg.get('role')
        content = msg.get('content', '')
        if role in ['user', 'assistant'] and content:
            formatted_messages.append({"role": role, "content": content})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=formatted_messages,
            temperature=0.7,
            max_tokens=1200
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        logger.error("OpenAI Rate Limit Exceeded in Personal Assistant")
        raise ValueError("OpenAI API rate limit exceeded. Please try again in a few moments.")
    except APIConnectionError:
        logger.error("OpenAI API Connection Error in Personal Assistant")
        raise ValueError("Network error connecting to OpenAI API. Please check server connectivity.")
    except Exception as e:
        logger.exception("Unexpected error in generate_assistant_response")
        raise ValueError(f"Unable to process assistant request: {str(e)}")
