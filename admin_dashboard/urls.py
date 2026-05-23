from django.urls import path
from .views import *



urlpatterns = [
    path("dashboard",dashboard,name="dashboard"),
    path("users/list",users_list,name="users_list"),
    path("blog/blog_list",blog_list,name="blog_list"),
    path("blog/create",blog_create,name="blog_create"),
    path("category_create",category_create,name="category_create"),
    path("create_tag",create_tag,name="create_tag"),
    path("blog_edit/<int:id>",blog_edit,name="blog_edit"),
    path("blog_delete/<int:id>",blog_delete,name="blog_delete"),
    path("blog_draft_list",blog_draft_list,name="blog_draft_list"),
    path("translations",translations,name="translations"),
    path("contect_list",contect_list,name="contect_list"),
    path("video_create",video_create,name="video_create"),
    path("videos_list",videos_list,name="videos_list"),
    path("video_category_create",video_category_create,name="video_category_create"),
    path("video_edit/<int:id>",video_edit,name="video_edit"),
    path("video_delete/<int:id>",video_delete,name="video_delete"),
    path("feedbacks",feedbacks,name="feedbacks"),
    path("survey_details",survey_details,name="survey_details"),
    path("blog_category_delete/<int:id>",blog_category_delete,name="blog_category_delete"),
    path("blog_tag_delete/<int:id>",blog_tag_delete,name="blog_tag_delete"),
    path("video_category_delete/<int:id>",video_category_delete,name="video_category_delete"),
    path("enquiry_details",enquiry_details,name="enquiry_details"),
    path("purchasing_details",purchasing_details,name="purchasing_details"),

    path('toggle-superuser/', toggle_superuser, name='toggle_superuser'),
]
