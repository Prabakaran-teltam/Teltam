from django.urls import path
from .views import *

urlpatterns = [
    
    path("",index,name="index"),
    path("login",log_in,name="login"),
    path("register",register,name="register"),
    path("verify_otp",verify_otp,name="verify_otp"),
    path('resend_otp/', resend_otp, name='resend_otp'),
    path('submit_review',submit_review,name='submit_review'),
    path('survey',survey,name='survey'),
    path("logout/",logout_view,name="logout"),
    path('profile',profile,name="profile"),
    # Password reset

    path('password_reset/', password_reset_request, name='password_reset_request'),
    path('password_reset/done/', password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', password_reset_complete, name='password_reset_complete'),
    
    # User pages
    path("home",home,name="home"),
    path("translations_history",translations_history,name="translations_history"),
    path("download_csv/<int:id>",download_csv,name="download_csv"),

    # Blog
    path("blog/view/<str:title>",view_blog,name="view_blog"),
    path('toggle-like/', toggle_like, name='toggle_like'),
    path('blog/list_of_blogs',list_of_blogs,name="list_of_blogs"),
    path("blog/tag_based_search/<str:tag>",tag_based_search,name="tag_based_search"),
    path("video/list_of_videos",list_of_videos,name="list_of_videos"),
    path("view_video/<int:id>",view_video,name="view_video"),
    path("about_us",about_us,name="about_us")
]

handler404 = 'main.views.custom_404'
