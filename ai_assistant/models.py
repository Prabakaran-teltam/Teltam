from django.db import models
from django.contrib.auth.models import User


class AIConversation(models.Model):
    """
    Stores conversation threads for AI Career Chatbot and AI Personal Assistant.
    Supports authenticated users and anonymous sessions.
    """
    ASSISTANT_TYPES = (
        ('career', 'AI Career Advisor'),
        ('assistant', 'AI Personal Assistant'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_conversations')
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    assistant_type = models.CharField(max_length=20, choices=ASSISTANT_TYPES, default='career')
    title = models.CharField(max_length=255, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        user_str = self.user.username if self.user else f"Session ({self.session_key[:8]})"
        return f"[{self.get_assistant_type_display()}] {user_str} - {self.title}"


class AIMessage(models.Model):
    """
    Stores individual messages inside an AIConversation thread.
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:40]}..."


class ResumeEvaluation(models.Model):
    """
    Stores resume evaluation records and AI feedback results.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='resume_evaluations')
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    target_role = models.CharField(max_length=255, blank=True)
    resume_filename = models.CharField(max_length=255)
    score = models.IntegerField(default=0)
    result_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else f"Session ({self.session_key[:8]})"
        return f"Resume ({self.resume_filename}) - Score: {self.score}/100 - {user_str}"
