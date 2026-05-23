from django.db import models
from django.contrib.auth.models import User
import random
from django.utils import timezone
from datetime import timedelta


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
    
    
    
class ClassInquiry(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inquiry from {self.full_name}"
    
    def __str__(self):
        return self.name



class Plan(models.Model):
    PLAN_CHOICES = [
        ('basic','basic'),
        ('pro', 'pro'),
        ('enterprise', 'enterprise')
    ]
    name = models.CharField(choices=PLAN_CHOICES,null=True,blank=False,unique=True)
    price = models.DecimalField(max_digits=8,decimal_places=2)
    period =  models.IntegerField(default=30)
    
    def __str__(self):
        return f"{self.get_name_display()} - ₹{self.price} / {self.period}"


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} - {self.status}"

class Subscription(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan,on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction,on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True,null=True)
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.end_date:
            duration = int(self.plan.period)
            self.end_date = self.start_date + timedelta(days=duration)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class Usage(models.Model):
    subscription = models.ForeignKey(Subscription,on_delete=models.CASCADE,related_name="usages")
    image_requests_used = models.IntegerField(default=0)
    pdf_requests_used = models.IntegerField(default=0)
    translations_used = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Usage for {self.subscription.user.username} ({self.subscription.plan.name})"


import uuid


# payments/models.py

class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]

    user       = models.OneToOneField(
                        User,
                     on_delete=models.CASCADE,
                     related_name='payment_subscription'
                 )
    plan_name  = models.CharField(max_length=20, choices=PLAN_CHOICES)   # ← plain string
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def __str__(self):
        return f"{self.user.email} → {self.plan_name} [{self.status}]"

# payments/models.py

class PaymentOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_order_id = models.CharField(max_length=100, unique=True)
    phonepe_order_id  = models.CharField(max_length=200, blank=True, null=True)

    user              = models.ForeignKey(
                            User,
                            on_delete=models.CASCADE,
                            related_name='payment_orders'
                        )
    plan_name         = models.CharField(max_length=20, choices=PLAN_CHOICES)  # ← plain string, no FK

    amount            = models.DecimalField(max_digits=10, decimal_places=2)
    currency          = models.CharField(max_length=5, default='INR')
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    phonepe_response  = models.JSONField(null=True, blank=True)

    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    paid_at           = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def amount_in_paise(self):
        return int(self.amount * 100)

    def __str__(self):
        return f"Order {self.merchant_order_id} | {self.user.email} | ₹{self.amount} [{self.status}]"
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_order_id = models.CharField(max_length=100, unique=True)     # sent to PhonePe
    phonepe_order_id = models.CharField(max_length=200, blank=True, null=True)  # returned by PhonePe

    # Relations
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_orders'
    )
    plan = models.CharField(max_length=20)
    # Payment info
    amount = models.DecimalField(max_digits=10, decimal_places=2)         # in ₹
    currency = models.CharField(max_length=5, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # PhonePe response data (raw)
    phonepe_response = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def amount_in_paise(self):
        return int(self.amount * 100)

    def __str__(self):
        return f"Order {self.merchant_order_id} | {self.user.email} | ₹{self.amount} [{self.status}]"
    
