from .models import Contact
from main.models import *

def notification_count(request):
    return {
        'new_contact_count': Contact.objects.filter(is_seen=False).count(),
        'new_users_count': UserProfile.objects.filter(is_seen=False).count(),
        'new_translations_count': Output_files.objects.filter(is_seen=False).count(),
        'new_review_count': User_Reviews.objects.filter(is_seen=False).count(),
        'new_survey_count': SurveyResponse.objects.filter(is_seen=False).count(),

    }