from celery import shared_task
from django.utils import timezone
from .models import BlogPost

@shared_task
def publish_scheduled_posts():
    now = timezone.now()
    posts = BlogPost.objects.filter(status='scheduled', published_at__lte=now)
    for post in posts:
        post.status = 'published'
        post.save()
