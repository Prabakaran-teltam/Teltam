import logging
from django.utils import timezone
from .models import PageViewLog

logger = logging.getLogger(__name__)

class PageViewTrackingMiddleware:
    """
    Middleware to automatically record page view analytics for Teltam AI platform.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Track only successful GET HTML requests
        if request.method == 'GET' and response.status_code == 200:
            path = request.path

            # Exclude internal asset and AJAX polling endpoints
            ignored_prefixes = [
                '/static/', '/media/', '/admin/', '/dashboard/',
                '/api/document-status/', '/api/task-status/', '/favicon.ico'
            ]
            if not any(path.startswith(prefix) for prefix in ignored_prefixes):
                self.log_page_view(request, path)

        return response

    def log_page_view(self, request, path):
        try:
            # Map paths to user-friendly page titles
            page_name_map = {
                '/': 'Homepage',
                '/ai-tools/': 'AI Tools',
                '/user/tools/text/': 'Text Translator',
                '/user/tools/file/': 'Document Translator',
                '/user/tools/voice/': 'Voice Translator',
                '/user/tools/camera/': 'Live Camera AR',
                '/user/dashboard/': 'User Overview',
                '/user/profile/': 'User Profile',
                '/user/history/': 'User Logs',
                '/user/api-keys/': 'API Keys Dashboard',
                '/pricing/': 'Pricing Plans',
                '/about/': 'About Us',
                '/contact/': 'Contact Us',
                '/blog/': 'Blog Articles',
                '/videos/': 'Video Tutorials',
                '/api-docs/': 'Developer API Docs',
                '/terms/': 'Terms & Conditions',
                '/terms-and-conditions/': 'Terms & Conditions',
                '/privacy/': 'Privacy Policy',
                '/privacy-policy/': 'Privacy Policy',
                '/refund-policy/': 'Refund Policy',
                '/refund/': 'Refund Policy',
            }

            page_name = page_name_map.get(path)
            if not page_name:
                if path.startswith('/blog/'):
                    page_name = 'Blog Article View'
                elif path.startswith('/videos/'):
                    page_name = 'Video Tutorial View'
                else:
                    page_name = 'Public Page'

            # Extract client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')

            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            user = request.user if request.user.is_authenticated else None

            # Create log entry
            PageViewLog.objects.create(
                path=path,
                page_name=page_name,
                user=user,
                ip_address=ip,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error logging page view for {path}: {e}")
