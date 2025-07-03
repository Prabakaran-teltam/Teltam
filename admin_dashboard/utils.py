from django.utils import timezone
from .models import BlogPost

def update_scheduled_posts():
    now = timezone.now()
    scheduled_posts = BlogPost.objects.filter(status='scheduled', published_at__lte=now)
    for post in scheduled_posts:
        post.status = 'published'
        post.save(update_fields=['status'])
