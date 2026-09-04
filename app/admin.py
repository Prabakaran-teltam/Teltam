from django.contrib import admin
from .models import Blog, YoutubeVideo, Contact, UserTranslationHistory, PricingPlan, UserSubscription, PaymentTransaction, DocumentTranslationHistory, AIClassEnquiry, BlogComment

@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'blog', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('user__username', 'user__email', 'blog__title', 'comment')

@admin.register(AIClassEnquiry)
class AIClassEnquiryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'email', 'phone_number', 'message')
    list_editable = ('status',)

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'scheduled_publish_date', 'created_date')
    list_filter = ('is_published', 'category', 'scheduled_publish_date')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(YoutubeVideo)
class YoutubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'created_date')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_date')
    list_filter = ('is_read',)

@admin.register(UserTranslationHistory)
class UserTranslationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'tool_type', 'source_lang', 'target_lang', 'created_date')

@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'plan_order', 'billing_cycle', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'is_upgrade', 'previous_plan', 'start_date', 'end_date')
    list_filter = ('status', 'is_upgrade')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('merchant_order_id', 'user', 'plan', 'amount', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(DocumentTranslationHistory)
class DocumentTranslationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'source_language', 'target_language', 'status', 'created_at')
    list_filter = ('status', 'source_language', 'target_language')
