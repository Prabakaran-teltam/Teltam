from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from .models import *
from .models import UserProfile

class UserRegisterForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control shadow-none','placeholder':'Enter username'}))
    email = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control shadow-none','placeholder':'Enter email address'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control shadow-none','placeholder':'Enter password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control shadow-none','placeholder':'Enter confirme password'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control','placeholder':'Address'}), required=False)
    phone = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Phone Number'}), required=False)
    gender = forms.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        widget=forms.Select(attrs={'class':'form-control'}),
        required=False
    )
    class Meta:
        model =User
        fields = ['username', 'email', 'password1', 'password2', 'address', 'phone', 'gender']
        
        
class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email
    
class PasswordResetForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput, label="New Password")
    new_password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm New Password")

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get('new_password1')
        new_password2 = self.cleaned_data.get('new_password2')
        if new_password1 != new_password2:
            raise forms.ValidationError("The passwords do not match.")
        return new_password2
    

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6,widget=forms.TextInput(attrs={
        'class' : 'form-control shadow-none',
        'placeholder':'Enter OTP'
    }))
    
class UserReviewForm(forms.ModelForm):
    class Meta:
        model = User_Reviews
        fields = ['name', 'review_text', 'star_rating']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'review_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Your Review'}),
            'star_rating': forms.HiddenInput()
        }



LANGUAGE_CHOICES = [
    ('tamil', 'Tamil'),
    ('telugu', 'Telugu'),
    ('kannada', 'Kannada'),
    ('hindi', 'Hindi'),
    ('english', 'English'),
    ('others', 'Others'),
]

class SurveyForm(forms.ModelForm):
    languages = forms.MultipleChoiceField(
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = SurveyResponse
        exclude = ['user']