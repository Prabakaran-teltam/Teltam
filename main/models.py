from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone



class UserProfile(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    is_seen = models.BooleanField(default=False) 
    
    class Meta:
        verbose_name = "User Self Details"
        verbose_name_plural = "User Self Details"

    def __str__(self):
        return self.user.username



class Translations(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    language = models.CharField(max_length=100,null=True, blank=False)
    target_language = models.CharField(max_length=100,null=True,blank=False)
    created = models.DateField(auto_now_add=True)
    is_seen = models.BooleanField(default=False) 


    class Meta:
        verbose_name = "Translation Details"
        verbose_name_plural = "Translation Details"

    def __str__(self):
        return self.user.username


class User_Reviews(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    name = models.CharField(max_length=100,null=True, blank=False)
    review_text = models.TextField()
    star_rating = models.IntegerField(null=True,blank=False)
    created = models.DateField(auto_now_add=True)
    is_seen = models.BooleanField(default=False) 
    
    
    class Meta:
        verbose_name = "Reviews"
        verbose_name_plural = "Reviews"

    def __str__(self):
        return self.user.username

    


class SurveyResponse(models.Model):
    REGISTER_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company / Organization'),
    ]
    INDUSTRY_CHOICES = [
        ('education', 'Education'),
        ('media', 'Media & Entertainment'),
        ('legal', 'Legal'),
        ('healthcare', 'Healthcare'),
        ('ecommerce', 'E-commerce'),
        ('others', 'Others'),
    ]
    FIND_US_CHOICES = [
        ('google', 'Google Search'),
        ('social', 'Social Media'),
        ('referral', 'Referral'),
        ('ads', 'Online Advertisement'),
        ('events', 'Events / Webinars'),
        ('others', 'Others'),
    ]
    PURPOSE_CHOICES = [
        ('personal', 'Personal Translation'),
        ('business', 'Business Use'),
        ('content', 'Content Creation'),
        ('academic', 'Academic / Research'),
        ('other', 'Other'),
    ]
    USAGE_CHOICES = [
        ('1-10', '1-10 Images'),
        ('11-50', '11-50 Images'),
        ('51-100', '51-100 Images'),
        ('100+', '100+ Images'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    register_as = models.CharField(max_length=50, choices=REGISTER_CHOICES)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    find_us = models.CharField(max_length=50, choices=FIND_US_CHOICES)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    languages = models.JSONField()
    usage = models.CharField(max_length=20, choices=USAGE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False) 
    
    
    class Meta:
        verbose_name = "Survey Details"
        verbose_name_plural = "Survey Details"
    

class Output_files(models.Model):
    translation = models.ForeignKey(Translations,on_delete=models.CASCADE)
    file = models.FileField(upload_to='outputs/')
    created = models.DateField(auto_now_add=True)
    is_seen = models.BooleanField(default=False) 
    
    class Meta:
        verbose_name = "Final "


    def __str__(self):
        return self.translation.user.username


class User_OTP(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)
    
    
    def generate_otp(self):
        self.otp = str(random.randint(100000,999999))
        self.save()
    
    def is_expired(self):
        return timezone.now() > self.created + timezone.timedelta(minutes=10)

class Newsletter(models.Model):
    email = models.EmailField(max_length=254)
    created = models.DateField(auto_now_add=True)
    is_seen = models.BooleanField(default=False) 