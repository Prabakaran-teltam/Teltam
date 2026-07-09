from .models import Contact

def dashboard_context(request):
    """
    Context processor to make dashboard-specific context variables
    available globally in all templates.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return {
            'global_unread_messages_count': Contact.objects.filter(is_read=False).count()
        }
    return {}
