import json
import logging
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from app.models import DeveloperAPIKey, UserSubscription

logger = logging.getLogger(__name__)

def developer_api_key_required(view_func):
    """
    Decorator for Developer REST API endpoints.
    Verifies Developer API Key and ensures the key owner has an active paid subscription plan.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        api_key = None

        # 1. Extract API Key from Request Headers
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                api_key = auth_header.split('Bearer ', 1)[1].strip()

        # 2. Extract API Key from GET parameters
        if not api_key:
            api_key = request.GET.get('api_key')

        # 3. Extract API Key from POST parameters or JSON payload
        if not api_key and request.method == 'POST':
            api_key = request.POST.get('api_key')
            if not api_key and request.content_type == 'application/json':
                try:
                    body = json.loads(request.body.decode('utf-8')) if request.body else {}
                    api_key = body.get('api_key')
                except Exception:
                    pass

        if not api_key:
            return JsonResponse({
                'status': 'error',
                'error': 'Authentication Required: Developer API key missing. Provide X-API-Key header, Authorization Bearer token, or api_key parameter.'
            }, status=401)

        # 4. Lookup API Key in database
        try:
            key_obj = DeveloperAPIKey.objects.select_related('user').get(api_key=api_key.strip())
        except DeveloperAPIKey.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Unauthorized: Invalid Developer API key provided.'
            }, status=401)

        if not key_obj.is_active:
            return JsonResponse({
                'status': 'error',
                'error': 'Forbidden: This Developer API key has been revoked or deactivated.'
            }, status=403)

        # 5. Enforce Subscription Access Control (Purchased Plan Users Only)
        has_active_sub = UserSubscription.objects.filter(user=key_obj.user, status='active').exists()
        if not has_active_sub:
            return JsonResponse({
                'status': 'error',
                'error': 'Subscription Required: Developer API access is restricted to active paid subscription plans. Please subscribe or renew your plan.'
            }, status=403)

        # 6. Update usage metrics
        key_obj.last_used_at = timezone.now()
        key_obj.usage_count += 1
        key_obj.save(update_fields=['last_used_at', 'usage_count'])

        # Attach objects to request
        request.api_key_obj = key_obj
        request.developer_user = key_obj.user

        return view_func(request, *args, **kwargs)

    return _wrapped_view
