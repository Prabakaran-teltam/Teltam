from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from django.contrib.auth.models import User
from django.contrib import messages
from main.models import *
from django.contrib.auth.decorators import user_passes_test
from .models import *
from django.db.models import Q
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags



def update_scheduled_posts():
    now = timezone.now()
    scheduled_posts = BlogPost.objects.filter(status='scheduled', published_at__lte=now)
    for post in scheduled_posts:
        post.status = 'published'
        post.save(update_fields=['status'])


@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    user_count = User.objects.count()
    if User.objects.exists():
        last_user = User.objects.latest('date_joined').date_joined.strftime('%b %d, %Y, %I:%M %p')
    else:
        last_user = "No users"

    translation_count = Translations.objects.count()
    if Translations.objects.exists():
        last_translation = Translations.objects.latest('created')
        last_translation_date = last_translation.created.strftime('%b %d, %Y')
        translation_details = Translations.objects.order_by('-created')[:5]
    else:
        last_translation_date = "No translations"
        translation_details = []

    blog_count = BlogPost.objects.count()
    if BlogPost.objects.exists():
        last_blog = BlogPost.objects.latest("created_at").created_at.strftime('%b %d, %Y')
    else:
        last_blog = "No blogs"

    return render(request, "admin/dashboard.html", {
        'user_count': user_count,
        'translation_count': translation_count,
        'blog_count': blog_count,
        'last_user': last_user,
        'last_translation_date': last_translation_date,
        'last_blog': last_blog,
        'translation_details': translation_details
    })

@user_passes_test(lambda u: u.is_superuser)
def users_list(request):
    query = request.GET.get("q", "")
    if query:
        user_data = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    else:
        user_data = User.objects.all()
    
    user_profile = UserProfile.objects.all()
    UserProfile.objects.filter(is_seen=False).update(is_seen=True)
    
    return render(request, "admin/users_list.html", {
        "user_data": user_data,
        "user_profile": user_profile
    })
    
    
@user_passes_test(lambda u: u.is_superuser)
def blog_list(request):
    blog_data = BlogPost.objects.all()
    return render(request,"admin/blog_list.html",{'blog_data':blog_data})

@user_passes_test(lambda u: u.is_superuser)
def blog_draft_list(request):
    blog_data = BlogPost.objects.filter(status="draft")
    return render(request,"admin/blog_draft_list.html",{'blog_data':blog_data})

@user_passes_test(lambda u: u.is_superuser)
def blog_create(request):
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)

        if form.is_valid():
            blog = form.save(commit=False)
            blog.title = blog.title.replace("/", ",")
            blog.save()

            # ✅ Get User emails
            user_emails = User.objects.filter(
                is_active=True
            ).exclude(email="").values_list("email", flat=True)

            # ✅ Get ClassInquiry emails
            inquiry_emails = ClassInquiry.objects.exclude(
                email=""
            ).values_list("email", flat=True)

            # ✅ Merge & remove duplicates
            all_emails = set(user_emails) | set(inquiry_emails)

            subject = "📰 New Blog Published on Teltam.in"
            from_email = "no-reply@teltam.in"

            # ✅ Send Emails
            for email in all_emails:
                if email == "admin@gmail.com":
                    continue

                html_content = render_to_string(
                    "admin/new_blog_notification.html",
                    {
                        "title": blog.title,
                        "author": request.user.username,
                        "link": request.build_absolute_uri(
                            f"/blog/view/{blog.title}"
                        ),
                    },
                )

                text_content = strip_tags(html_content)

                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    from_email,
                    [email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()

            messages.success(
                request,
                "✅ Blog created and email notifications sent to all users (including inquiries).",
            )
            return redirect("blog_list")

        else:
            messages.error(request, form.errors)

    else:
        form = BlogPostForm()
        category_form = CategoryForm()
        tag_form = TagForm()
        category_list = Category.objects.all()
        tag_list = Tag.objects.all()

    return render(
        request,
        "admin/blog_create.html",
        {
            "form": form,
            "category_form": category_form,
            "tag_form": tag_form,
            "category_list": category_list,
            "tag_list": tag_list,
        },
    )

@user_passes_test(lambda u: u.is_superuser)
def blog_edit(request,id):
    blog = get_object_or_404(BlogPost,id=id)
    if request.method == "POST":
        form = BlogPostForm(request.POST,request.FILES,instance=blog)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.title = blog.title.replace("/", ",")
            blog.save()
            messages.success(request,"Blog Edited...")
            return redirect("blog_list")
        else:
            messages.error(request,form.errors)
    else:
        form=BlogPostForm(instance=blog)
        category_form = CategoryForm()
        tag_form = TagForm()
        category_list = Category.objects.all()
        tag_list = Tag.objects.all()
    return render(request,"admin/blog_edit.html",{'form':form,"category_form":category_form,"tag_form":tag_form,"category_list":category_list,"tag_list":tag_list})


@user_passes_test(lambda u:u.is_superuser)
def blog_delete(request,id):
    res = BlogPost.objects.get(id=id)
    res.delete()
    messages.success(request, 'Blog has been deleted')
    return redirect('blog_list')
    
@user_passes_test(lambda u:u.is_superuser)
def category_create(request):
    form = CategoryForm(request.POST)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request,"Category Added...")
            return redirect('blog_create')
        else:
            messages.error(request,form.errors)
            return redirect('blog_create')

@user_passes_test(lambda u:u.is_superuser)
def blog_category_delete(request,id):
    res = Category.objects.get(id=id)
    res.delete()
    messages.success(request,"Blog category has been deleted...")
    return redirect("blog_create")


@user_passes_test(lambda u:u.is_superuser)
def blog_tag_delete(request,id):
    res = Tag.objects.get(id=id)
    res.delete()
    messages.success(request,"Blog tag has been deleted...")
    return redirect("blog_create")


@user_passes_test(lambda u:u.is_superuser)
def video_category_delete(request,id):
    res = VideoCategory.objects.get(id=id)
    res.delete()
    messages.success(request,"Video category has been deleted...")
    return redirect("video_create")


@user_passes_test(lambda u:u.is_superuser)
def create_tag(request):
    form = TagForm(request.POST)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request,"Tag Added...")
            return redirect("blog_create")
        else:
            messages.error(request,form.errors)
            return redirect("blog_create")


@user_passes_test(lambda u:u.is_superuser)
def translations(request):
    
    output_files = Output_files.objects.all()
    Output_files.objects.filter(is_seen=False).update(is_seen=True)
    return render(request,"admin/translations.html",{'Output_files':output_files})


@user_passes_test(lambda u:u.is_superuser)
def contect_list(request):
    message = Contact.objects.all()
    Contact.objects.filter(is_seen=False).update(is_seen=True)
    return render(request,"admin/contect_list.html",{'message':message})


@user_passes_test(lambda u: u.is_superuser)
def video_create(request):
    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Video saved..")
            return redirect("videos_list")
        else:
            messages.error(request, form.errors)
    else:
        form = VideoForm()
    category_list = VideoCategory.objects.all()
    category_form = VideoCategoryForm()
    return render(request, "admin/video_create.html", {
        'form': form,
        'category_list': category_list,
        'category_form': category_form
    })

@user_passes_test(lambda u:u.is_superuser)
def video_edit(request,id):
    blog = get_object_or_404(Video,id=id)
    if request.method == "POST":
        form = VideoForm(request.POST,request.FILES,instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request,"Video Edited...")
            return redirect("videos_list")
        else:
            messages.error(request,form.errors)
    else:
        form=VideoForm(instance=blog)
        category_form = VideoCategoryForm()
        category_list = Category.objects.all()
    return render(request,"admin/video_edit.html",{'form':form,"category_form":category_form,"category_list":category_list})


@user_passes_test(lambda u:u.is_superuser)
def video_delete(request,id):
    res = Video.objects.get(id=id)
    res.delete()
    messages.success(request, 'Video has been deleted')
    return redirect('videos_list')


@user_passes_test(lambda u:u.is_superuser)
def video_category_create(request):
    form = VideoCategoryForm(request.POST)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request,"Category Added...")
            return redirect('video_create')
        else:
            messages.error(request,form.errors)
            return redirect('video_create')


@user_passes_test(lambda u:u.is_superuser)
def videos_list(request):
    data = Video.objects.all()
    return render(request,"admin/videos_list.html",{'data':data})


@user_passes_test(lambda u:u.is_superuser)
def feedbacks(request):
    feedbacks = User_Reviews.objects.all()
    User_Reviews.objects.filter(is_seen=False).update(is_seen=True)
    return render(request,"admin/feedbacks.html",{"feedbacks":feedbacks})


@user_passes_test(lambda u:u.is_superuser)
def survey_details(request):
    SurveyResponse.objects.filter(is_seen=False).update(is_seen=True)
    data = SurveyResponse.objects.all()
    return render(request,"admin/survey_details.html",{'data':data})




@user_passes_test(lambda u:u.is_superuser)
def enquiry_details(request):
    data = ClassInquiry.objects.all()
    return render(request,"admin/enquiry_details.html",{'data':data})




@user_passes_test(lambda u: u.is_staff)
def toggle_superuser(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        is_superuser = 'is_superuser' in request.POST  # checkbox only sends when checked
        try:
            user = User.objects.get(id=user_id)
            user.is_superuser = is_superuser
            user.save()

            # Email content
            status_text = "granted" if is_superuser else "revoked"
            subject = f"Admin Privileges {status_text.capitalize()}"
            from_email = "no-reply@yourdomain.com"
            to_email = [user.email]

            html_content = render_to_string("admin/admin_privilege_notification.html", {
                "user": user,
                "status_text": status_text
            })
            text_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            messages.success(request, f"Superuser access {status_text} for {user.username}.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect(request.META.get('HTTP_REFERER', '/'))

@user_passes_test(lambda u:u.is_superuser)
def purchasing_details(request):
    subscriptions = Subscription.objects.select_related('transaction', 'plan', 'user').all().order_by('-transaction__created_at')
    return render(request, "admin/purchases_list.html", {"subscriptions": subscriptions})
