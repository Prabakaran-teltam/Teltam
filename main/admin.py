from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm



admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(Translations)
class TranslationAdmin(ModelAdmin):
    list_display = ['user','language','created']
    list_filter = ['user']

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ['user','gender','phone']


@admin.register(SurveyResponse)
class SurveyResponseAdmin(ModelAdmin):
    list_display = ['user','industry','find_us']

@admin.register(User_Reviews)
class User_ReviewsAdmin(ModelAdmin):
    list_display = ['user','name','star_rating']

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm




