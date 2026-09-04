from django import forms
from django.contrib.auth.models import User
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import Blog, YoutubeVideo, Contact

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            'title', 'slug', 'category', 'short_description', 'full_content', 
            'featured_image', 'author', 'tags', 'meta_title', 'meta_description', 
            'is_published', 'scheduled_publish_date', 'send_email_notification'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg fw-bold', 'placeholder': 'Enter a catchy article title...'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'custom-url-slug (auto-generated if empty)'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AI Translation, Technology, Guides'}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a compelling short summary that appears on blog listing cards...'}),
            'full_content': CKEditorUploadingWidget(config_name='default', attrs={'class': 'form-control'}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'id': 'featuredImageInput'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author name'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AI, Machine Translation, Neural Network'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Meta Title (recommended 50-60 characters)'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'SEO Meta Description (recommended 120-160 characters)'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'scheduled_publish_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'send_email_notification': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

class YoutubeVideoForm(forms.ModelForm):
    class Meta:
        model = YoutubeVideo
        fields = [
            'title', 'youtube_video_url', 'youtube_video_id', 'thumbnail_image', 
            'category', 'short_description', 'full_description', 'tags', 
            'meta_title', 'meta_description', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter video title'}),
            'youtube_video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'youtube_video_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YouTube Video ID (auto-extracted if left blank)'}),
            'thumbnail_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Product Setup'}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter short teaser description'}),
            'full_description': CKEditorUploadingWidget(config_name='default', attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma-separated tags, e.g. Setup, Tutorial'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Meta Title (defaults to title)'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'SEO Meta Description'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'subject', 'message']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'email']
        labels = {
            'first_name': 'Full Name',
            'email': 'Email Address'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
        }

