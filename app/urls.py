from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('pricing/', views.pricing, name='pricing'),
    path('ai-tools/', views.ai_tools, name='ai_tools'),
    path('contact/', views.contact, name='contact'),
    
    # Public dynamic blog & video pages
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_view, name='blog_view'),
    path('videos/', views.video_list, name='video_list'),
    path('videos/<slug:slug>/', views.video_view, name='video_view'),
    
    # Public user authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Translators API Playground endpoints
    path('api/translate/', views.translate_api, name='translate_api'),
    path('api/upload-document/', views.upload_document, name='upload_document'),
    path('api/document-status/<str:task_id>/', views.document_task_status, name='document_task_status'),
    path('download/document/<int:id>/', views.download_translated_file, name='download_translated_file'),
    path('api/upload-voice/', views.upload_voice_api, name='upload_voice_api'),
    path('api/task-status/<str:task_id>/', views.task_status_api, name='task_status_api'),

    # =====================================================================
    # CUSTOM ADMIN DASHBOARD CONSOLE PATHS
    # =====================================================================
    path('dashboard/login/', views.dashboard_login, name='dashboard_login'),
    path('dashboard/logout/', views.dashboard_logout, name='dashboard_logout'),
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    
    # Blog CRUD in Dashboard
    path('dashboard/blogs/', views.dashboard_blog_list, name='dashboard_blog_list'),
    path('dashboard/blogs/add/', views.dashboard_blog_add, name='dashboard_blog_add'),
    path('dashboard/blogs/edit/<int:pk>/', views.dashboard_blog_edit, name='dashboard_blog_edit'),
    path('dashboard/blogs/delete/<int:pk>/', views.dashboard_blog_delete, name='dashboard_blog_delete'),
    
    # YouTube Video CRUD in Dashboard
    path('dashboard/videos/', views.dashboard_video_list, name='dashboard_video_list'),
    path('dashboard/videos/add/', views.dashboard_video_add, name='dashboard_video_add'),
    path('dashboard/videos/edit/<int:pk>/', views.dashboard_video_edit, name='dashboard_video_edit'),
    path('dashboard/videos/delete/<int:pk>/', views.dashboard_video_delete, name='dashboard_video_delete'),
    
    # Contact Submissions Review in Dashboard
    path('dashboard/contacts/', views.dashboard_contact_list, name='dashboard_contact_list'),
    path('dashboard/contacts/view/<int:pk>/', views.dashboard_contact_view, name='dashboard_contact_view'),
    path('dashboard/contacts/mark-read/<int:pk>/', views.dashboard_contact_mark_read, name='dashboard_contact_mark_read'),
    path('dashboard/contacts/mark-unread/<int:pk>/', views.dashboard_contact_mark_unread, name='dashboard_contact_mark_unread'),
    
    # Registered Users management in Dashboard
    path('dashboard/users/', views.dashboard_user_list, name='dashboard_user_list'),
    path('dashboard/payments/', views.dashboard_payment_list, name='dashboard_payment_list'),
    path('dashboard/subscriptions/', views.dashboard_subscription_list, name='dashboard_subscription_list'),

    # =====================================================================
    # PHONEPE V2 PAYMENT INTEGRATION PATHS
    # =====================================================================
    path('pricing/select/<slug:plan_slug>/', views.pricing_select, name='pricing_select'),
    path('checkout/<slug:plan_slug>/', views.checkout, name='checkout'),
    path('payment/initiate/<slug:plan_slug>/', views.payment_initiate, name='payment_initiate'),
    path('payment/phonepe/status/', views.payment_redirect, name='payment_redirect'),
    path('payment/phonepe/callback/', views.payment_webhook, name='payment_webhook'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    path('payment/pending/', views.payment_pending, name='payment_pending'),

    # =====================================================================
    # USER DASHBOARD CONSOLE PATHS
    # =====================================================================
    path('user/dashboard/', views.user_dashboard_home, name='user_dashboard_home'),
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/profile/password/', views.user_change_password, name='user_change_password'),
    path('user/tools/text/', views.user_tool_text, name='user_tool_text'),
    path('user/tools/file/', views.user_tool_file, name='user_tool_file'),
    path('user/tools/voice/', views.user_tool_voice, name='user_tool_voice'),
    path('user/history/', views.user_history_list, name='user_history_list'),
    path('user/logout/', views.user_logout, name='user_logout'),
]

