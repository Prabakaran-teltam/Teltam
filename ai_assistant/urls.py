from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('career/', views.career_chat_api, name='career_chat_api'),
    path('resume/', views.evaluate_resume_api, name='evaluate_resume_api'),
    path('assistant/', views.assistant_chat_api, name='assistant_chat_api'),
    path('clear-chat/', views.clear_chat_api, name='clear_chat_api'),
]
