from django import forms
from .models import BlogPost, Category, Tag, Contact,Video, VideoCategory
from django.contrib.auth.models import User
from django_ckeditor_5.widgets import CKEditor5Widget
from captcha.fields import CaptchaField


class BlogPostForm(forms.ModelForm):
    content = forms.CharField(
        widget=CKEditor5Widget(config_name='default'),
        required=False
    )
    class Meta:
        model = BlogPost
        fields = [
            'title',
            'author',
            'content',
            'image',
            'video_url',
            'published_at',
            'status',
            'category',
            'tags',
            'meta_title',
            'meta_description',
            'show_cta',
            'cta_text',
            'cta_link',
            'comment_show_status'
        ]


        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
            'published_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
                        'tags': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'id': 'tags', 
            }),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'show_cta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cta_text': forms.TextInput(attrs={'class': 'form-control'}),
            'cta_link': forms.URLInput(attrs={'class': 'form-control'}),
            'comment_show_status' : forms.CheckboxInput(attrs={'class': 'form-check-input','type':'checkbox'}),
        }


    def __init__(self, *args, **kwargs):
        super(BlogPostForm, self).__init__(*args, **kwargs)
        self.fields['author'].queryset = User.objects.filter(is_superuser=True)
        self.fields['tags'].queryset = Tag.objects.all()
        self.fields['category'].queryset = Category.objects.all()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            })
        }

class VideoCategoryForm(forms.ModelForm):
    class Meta:
        model = VideoCategory
        fields = ['name']
        widgets = {
            'name':forms.TextInput(attrs={
                'class' : 'form-control',
                'placeholder' : 'Enter category name'
            })
        }
        
        
                
class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']
        widgets = {
            'name':forms.TextInput(attrs={
                'class':'form-control',
                'placeholder':'Enter tag name'
            })
        }
        
        
class ContactForm(forms.ModelForm):
    captcha = CaptchaField()
    class Meta:
        model = Contact
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control shadow-none',
                'placeholder': 'Your Name',
                'required': 'required'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control shadow-none',
                'placeholder': 'Your Email',
                'required': 'required'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control shadow-none',
                'placeholder': 'Message',
                'rows': 6,
                'required': 'required'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['captcha'].widget.attrs.update({
            'class': 'form-control shadow-none',
            'placeholder': 'Enter Captcha'
        })
        
class VideoForm(forms.ModelForm):
    description = forms.CharField(
        widget=CKEditor5Widget(config_name='default'),
        required=False
    )
    class Meta:
        model = Video
        fields = ['category', 'title', 'description', 'youtube_url', 'thumbnail_image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Title'}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'YouTube URL'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'thumbnail_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }