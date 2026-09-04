import os
import urllib.parse as urlparse
from django.db import models
from django.utils.text import slugify

from django.contrib.auth.models import User

import re

def extract_youtube_id(url):
    """
    Robust function to extract clean 11-character YouTube video ID from any format.
    """
    if not url:
        return ""
    pattern = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?|shorts)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(pattern, str(url))
    if match:
        return match.group(1)
    clean_str = str(url).strip()
    if len(clean_str) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', clean_str):
        return clean_str
    return ""

class Blog(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.CharField(max_length=100)
    short_description = models.TextField()
    full_content = models.TextField()
    featured_image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    author = models.CharField(max_length=100, default='Admin')
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    scheduled_publish_date = models.DateTimeField(blank=True, null=True, help_text="Set a future date and time to schedule automatic publishing.")
    send_email_notification = models.BooleanField(default=True, help_text="Designates whether email notification should be sent to registered users upon publishing.")
    is_notification_sent = models.BooleanField(default=False, help_text="Designates whether email notification has been sent to registered users.")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    @property
    def is_live(self):
        """
        Returns True if the article is marked as published AND its scheduled publish date (if set) has arrived.
        """
        from django.utils import timezone
        if not self.is_published:
            return False
        if self.scheduled_publish_date and self.scheduled_publish_date > timezone.now():
            return False
        return True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            orig = self.slug
            count = 1
            while Blog.objects.filter(slug=self.slug).exists():
                self.slug = f"{orig}-{count}"
                count += 1
        if not self.meta_title:
            self.meta_title = self.title
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_date']

class YoutubeVideo(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    youtube_video_url = models.URLField(max_length=500)
    youtube_video_id = models.CharField(max_length=50, blank=True)
    thumbnail_image = models.ImageField(upload_to='videos/', blank=True, null=True)
    category = models.CharField(max_length=100)
    short_description = models.TextField()
    full_description = models.TextField()
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            orig = self.slug
            count = 1
            while YoutubeVideo.objects.filter(slug=self.slug).exists():
                self.slug = f"{orig}-{count}"
                count += 1
        if not self.youtube_video_id:
            self.youtube_video_id = extract_youtube_id(self.youtube_video_url)
        if not self.meta_title:
            self.meta_title = self.title
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_date']

class Contact(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_date']

class UserTranslationHistory(models.Model):
    TOOL_CHOICES = [
        ('text', 'Text Translator'),
        ('file', 'File Translator'),
        ('voice', 'Voice Translator'),
        ('camera', 'Live Camera Translator'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='translation_history')
    tool_type = models.CharField(max_length=20, choices=TOOL_CHOICES)
    source_text = models.TextField()
    translated_text = models.TextField(blank=True, null=True)
    transliterated_text = models.TextField(blank=True, null=True)
    source_lang = models.CharField(max_length=50)
    target_lang = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return f"{self.user.username} - {self.get_tool_type_display()} ({self.created_date.strftime('%Y-%m-%d %H:%M')})"


class PricingPlan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, default='monthly') # monthly / yearly
    plan_order = models.PositiveIntegerField(default=1, help_text="Priority level (e.g. 1=Basic, 2=Pro, 3=Business)")
    features = models.TextField(help_text="Newline separated features list")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.billing_cycle})"

    def get_features_list(self):
        return [f.strip() for f in self.features.split('\n') if f.strip()]

class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    payment_transaction = models.ForeignKey('PaymentTransaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_upgrade = models.BooleanField(default=False)
    previous_plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='upgraded_from_subscriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"

class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    merchant_order_id = models.CharField(max_length=100, unique=True)
    phonepe_order_id = models.CharField(max_length=100, blank=True, null=True)
    phonepe_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_payload = models.TextField(blank=True, null=True)
    response_payload = models.TextField(blank=True, null=True)
    callback_payload = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.merchant_order_id} - {self.status} (₹{self.amount})"


class DocumentTranslationHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failure', 'Failure'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_translations', null=True, blank=True)
    original_file = models.FileField(upload_to='documents/originals/', null=True, blank=True)
    extracted_text = models.TextField(blank=True, null=True)
    translated_text = models.TextField(blank=True, null=True)
    transliterated_text = models.TextField(blank=True, null=True)
    source_language = models.CharField(max_length=50)
    target_language = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    download_file = models.FileField(upload_to='documents/translated/', null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.user.username if self.user else "Anonymous"
        return f"{user_display} - {self.source_language} to {self.target_language} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class DeveloperAPIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100, default='Default Secret Key')
    api_key = models.CharField(max_length=128, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name} ({'Active' if self.is_active else 'Inactive'})"

    @staticmethod
    def generate_key():
        import secrets
        return f"teltam_sk_{secrets.token_urlsafe(32)}"


class PageViewLog(models.Model):
    path = models.CharField(max_length=255, db_index=True)
    page_name = models.CharField(max_length=100, default='Page View')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='page_views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else 'Guest'
        return f"{self.page_name} ({self.path}) - {user_str} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AIClassEnquiry(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('enrolled', 'Enrolled'),
        ('cancelled', 'Cancelled'),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    message = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "AI Class Enquiry"
        verbose_name_plural = "AI Class Enquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email}) - {self.phone_number}"


from django.db.models.signals import post_save
class BlogComment(models.Model):
    """Stores user comments posted on blog articles."""
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.blog.title}"


from django.dispatch import receiver

@receiver(post_save, sender=Blog)
def on_blog_post_saved(sender, instance, created, **kwargs):
    """
    Signal handler that triggers asynchronous mass email dispatch to registered users
    when a Blog post is published (is_published=True), send_email_notification is enabled,
    and notifications haven't been sent yet.
    """
    if instance.is_live and instance.send_email_notification and not instance.is_notification_sent:
        try:
            from app.tasks import send_new_blog_notifications_task
            
            celery_active = False
            try:
                from project.celery import app as celery_app
                inspect = celery_app.control.inspect(timeout=0.15)
                pings = inspect.ping() if inspect else None
                celery_active = bool(pings)
            except Exception:
                celery_active = False

            if celery_active:
                send_new_blog_notifications_task.delay(instance.id)
            else:
                import threading
                def run_thread():
                    try:
                        send_new_blog_notifications_task(instance.id)
                    except Exception as err:
                        logging.getLogger(__name__).exception(f"Error in blog notification thread: {err}")

                t = threading.Thread(target=run_thread, daemon=True)
                t.start()
        except Exception as sig_err:
            logging.getLogger(__name__).exception(f"Failed to trigger blog notification signal: {sig_err}")



