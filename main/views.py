from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .forms import *
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .forms import PasswordResetRequestForm
from .forms import PasswordResetForm
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import messages
import cv2
from deep_translator import GoogleTranslator
from indic_transliteration.sanscript import transliterate, IAST
from indic_transliteration import sanscript
import os
import pandas as pd
from .models import *
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.files import File
import shutil
from django.core.mail import EmailMultiAlternatives
from admin_dashboard.models import *
from django.urls import reverse
from admin_dashboard.utils import *
from admin_dashboard.forms import *
import openai
from pdf2image import convert_from_path
import base64
from openai import OpenAI
from decouple import config
from time import sleep
import re
from django.http import FileResponse


# Payment code 
import base64, json, hashlib, requests
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse

from dateutil.relativedelta import relativedelta
from django.utils.timezone import now

# POPPLER_PATH = "C:\Release-24.08.0-0\poppler-24.08.0\Library\bin"
# POPPLER_PATH = ""

api_key = config('OPENAI_API_KEY')
openai_client = OpenAI(api_key=api_key)


def index(request):
    img = Translations.objects.all().count()
    clients = User.objects.all().count
    reviews = User_Reviews.objects.filter(star_rating=5)[:6]
    blog = BlogPost.objects.filter(status="published")[:3]
    video = Video.objects.filter(is_active=True)[:3]
    for v in video:
        match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', v.youtube_url)
        v.video_id = match.group(1) if match else None
    update_scheduled_posts()
    form = ContactForm()
    enquiry_form = ClassEnquiryForm()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent. Thank you!")
            return redirect('index')
        else:
            messages.error(request,"Invalid Captcha.")
            return redirect('index')
    return render(request,'index.html',{'img':img,'clients':clients,'reviews':reviews,'blog':blog,'form':form,'video':video,'enquiry_form':enquiry_form})


from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def newsletter(request):
    if request.method == "POST":
        email = request.POST.get("email")
        res = Newsletter(email=email)
        res.save()
        subject = "Welcome to Teltam.in Newsletter"
        from_email = "no-reply@teltam.in"
        to = [email]
        html_content = render_to_string("newsletter_welcome_email.html", {'email': email})
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        messages.success(request, "Thank you for subscribing!")
        return redirect("index")


def view_blog(request,title):
    blog = BlogPost.objects.get(title=title)
    id = blog.id
    related_blog = BlogPost.objects.filter(category=blog.category).filter(status="published").exclude(title=id)
    comments = Comment.objects.filter(post=id)
    is_liked = False
    if request.user.is_authenticated:
        is_liked = Like.objects.filter(post=blog, user=request.user).exists()
    if request.method == "POST":
        content = request.POST.get('content')
        res = Comment(post=blog,user=request.user,comment=content)
        res.save()
        messages.success(request,"Your comment has been posted.")
        return redirect(reverse("view_blog", args=[id]))
    return render(request,"view_blog.html",{'blog':blog,'related_blog':related_blog,'comments':comments,'is_liked':is_liked})



def view_video(request,id):
    video = Video.objects.get(id=id)
    return render(request,"view_video.html",{'video':video})



@login_required
def toggle_like(request):
    if request.method == "POST":
        post_id = request.POST.get("post_id")
        post = BlogPost.objects.get(id=post_id)
        user = request.user
        liked = False
        existing_like = Like.objects.filter(post=post, user=user)
        if existing_like.exists():
            existing_like.delete()
        else:
            Like.objects.create(post=post, user=user)
            liked = True
        like_count = post.like.count()
        return JsonResponse({"liked": liked, "like_count": like_count})


 
def list_of_blogs(request):
    blogs = BlogPost.objects.filter(status="published")
    categories = Category.objects.all()
    enquiry_form = ClassEnquiryForm()
    return render(request,"list_of_blogs.html",{'blogs':blogs,'categories':categories,'enquiry_form':enquiry_form})



def list_of_videos(request):
    videos = Video.objects.filter(is_active=True)
    for v in videos:
        match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', v.youtube_url)
        v.video_id = match.group(1) if match else None
    enquiry_form = ClassEnquiryForm()
    return render(request,"list_of_videos.html",{'videos':videos,'enquiry_form':enquiry_form})



def tag_based_search(request,tag):
    tag = Tag.objects.get(name=tag)
    blogs = BlogPost.objects.filter(tags=tag)
    return render(request,"list_of_blogs.html",{"blogs":blogs})

 
def about_us(reqeust):
    enquiry_form = ClassEnquiryForm()
    return render(reqeust,"about_us.html",{'enquiry_form':enquiry_form})



def log_in(request):
    error_message = None
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get("username")
        pws = request.POST.get("password")
        user = authenticate(request, username=name, password=pws)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                messages.success(request,"Welcome back to Teltam Administrator")
                return redirect("dashboard")
            else:
                login(request, user)
                next_url = request.POST.get("next") or "home"
                messages.success(request,f"Welcome back to Teltam {request.user}...!")
                return redirect(next_url)
        else:
            messages.error(request,"Invalid username or password.")
            return redirect('login')
    return render(request, 'login.html', {'error_message': error_message})



def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()


            # Create user profile
            UserProfile.objects.create(
                user=user,
                address=form.cleaned_data.get('address'),
                phone=form.cleaned_data.get('phone'),
                gender=form.cleaned_data.get('gender')
            )

            # Generate OTP
            otp_entry, _ = User_OTP.objects.get_or_create(user=user)
            otp_entry.generate_otp()

            # Prepare HTML email content
            
            context = {
                'otp': otp_entry.otp,
                'logo_url': 'http://127.0.0.1:8000/static/assets/img/logo.png',  # Update with your actual logo URL
            }
            html_content = render_to_string('otp_mail.html', context)
            text_content = f'Your OTP is {otp_entry.otp}'

            subject = 'Your OTP Code'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            # Save user ID in session and redirect
            request.session['user_id'] = user.id
            messages.info(request, 'We sent an OTP to your email.')
            return redirect('verify_otp')
    else:
        form = UserRegisterForm()
    return render(request, "register.html", {'form': form})



def verify_otp(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('register')

    user = User.objects.get(id=user_id)
    otp_record = User_OTP.objects.get(user=user)

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            if otp_record.is_expired():
                otp_record.delete()
                messages.error(request, "OTP expired. Please request a new one.")
                return redirect('verify_otp')

            if form.cleaned_data['otp'] == otp_record.otp:
                user.is_active = True
                user.save()
                otp_record.delete()
                login(request, user)
                messages.success(request, 'Registration successful and verified.')

                # ✅ Send welcome email
                subject = "🎉 Welcome to Teltam.in!"
                from_email = "no-reply@teltam.in"
                to_email = [user.email]

                html_content = render_to_string(
                    "welcome_email.html",
                    {"user": user, "site_name": "Teltam.in"},
                )
                text_content = strip_tags(html_content)

                msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                return redirect('survey')
            else:
                messages.error(request, 'Invalid OTP')
                return redirect('verify_otp')
    else:
        form = OTPForm()

    return render(request, 'verify_otp.html', {'form': form})



def resend_otp(request):
    user_id = request.session.get('user_id')
    if request.user.is_authenticated:
        return redirect('home')
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')
    user = User.objects.get(id=user_id)
    otp_record, _ = User_OTP.objects.get_or_create(user=user)
    # Only resend if previous OTP is expired or 1 minute has passed
    if not otp_record.is_expired() and (timezone.now() - otp_record.created).seconds < 60:
        messages.warning(request, "Please wait before requesting a new OTP.")
        return redirect('verify_otp')
    otp_record.generate_otp()
    send_mail(
        subject='Your New OTP Code',
        message=f'Your new OTP is {otp_record.otp}',
        from_email='youremail@example.com',
        recipient_list=[user.email],
    )
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('verify_otp')



@login_required
def survey(request):
    if not request.user.is_authenticated:
        messages.warning(request,'Login required. Please sign in to continue')
        return redirect('index')
    already_filled = SurveyResponse.objects.filter(user=request.user).exists()
    if already_filled:
        return redirect('home')
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.user = request.user
            survey.save()
            messages.success(request,'We’ve received your response. Thank you for your time!')
            return redirect('home')
        else:
            messages.error(request,'Something went wrong. Please try again later.')
            return redirect('survey')
    else:
        form = SurveyForm()
    return render(request, 'survey.html', {
        'form': form,
        'industry_choices': SurveyResponse.INDUSTRY_CHOICES,
        'find_us_choices': SurveyResponse.FIND_US_CHOICES,
        'purpose_choices': SurveyResponse.PURPOSE_CHOICES,
        'usage_choices': SurveyResponse.USAGE_CHOICES,
        'language_choices': LANGUAGE_CHOICES,
    })



@login_required
def profile(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in...!')
        return redirect('index')
    profile = UserProfile.objects.get(user=request.user)
    return render(request,'profile.html',{'profile':profile})



@login_required
def logout_view(request):
    logout(request)
    messages.success(request,"Logout Successful..!")
    return redirect('index')



def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(str(user.pk).encode())
                current_site = get_current_site(request)
                mail_subject = 'Password Reset Request'
                message = render_to_string('registration/password_reset_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': uid,
                    'token': token,
                })
                send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                messages.success(request, 'Password reset link has been sent to your email address.')
                return redirect('password_reset_done')
            except User.DoesNotExist:
                messages.error(request, 'Email address not found.')
                return redirect('password_reset_request')
        else:
            for field in form.errors:
                messages.error(request, form.errors[field])
    else:
        form = PasswordResetRequestForm()
    return render(request, 'registration/password_reset_request.html', {'form': form})



def password_reset_done(request):
    return render(request, 'registration/password_reset_done.html')



def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetForm(user, request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                messages.success(request, 'Your password has been successfully reset.')
                return redirect('password_reset_complete')
            else:
                for field in form:
                    for error in field.errors:
                        messages.error(request, error)
        else:
            form = PasswordResetForm(user)
        return render(request, 'registration/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset_invalid')



def password_reset_complete(request):
    return render(request, 'registration/password_reset_complete.html')



# =========== User Dashboard Details ==============
# Edited
lang_map = {
    "tamil": ("ta",sanscript.TAMIL),
    "telugu": ("te", sanscript.TELUGU),
    "hindi": ("hi", sanscript.DEVANAGARI),
    "malayalam": ("ml", sanscript.MALAYALAM),
    "kannada": ("kn", sanscript.KANNADA),
    "english":('en', sanscript.ITRANS)
}

 
def preprocess_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


# Edited
def translate_with_chatgpt_batch(words, source_lang, target_lang):
    try:
        prompt = f"Translate the following words from {source_lang} to {target_lang}. " \
                 f"Return ONLY the translations in the same order, separated by commas.\n\n" \
                 f"{', '.join(words)}"

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        output = response.choices[0].message.content.strip()

        # Convert back into list
        translations = [w.strip() for w in output.split(",")]
        if len(translations) != len(words):
            # fallback: pad/truncate
            translations = (translations + [None] * len(words))[:len(words)]
        return translations
    except:
        return [None] * len(words)


def get_transliterations_chatgpt(words, source_language, target_language):
    source_lang_code, source_script = lang_map[source_language]
    target_lang_code, target_script = lang_map[target_language]

    output_data = []

    # ✅ Batch request for meanings
    target_meanings = translate_with_chatgpt_batch(words, source_language, target_language)
    english_meanings = translate_with_chatgpt_batch(words, source_language, "English")

    for i, word in enumerate(words):
        try:
            target_transliteration = transliterate(word, source_script, target_script)
            english_transliteration = transliterate(word, source_script, sanscript.IAST)

            output_data.append([
                word,
                target_transliteration,
                target_meanings[i],
                english_transliteration,
                english_meanings[i]
            ])
        except:
            output_data.append([word, None, None, None, None])

    return output_data
# Translater with using Chat GPT API key



def extract_text_from_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            image_file.seek(0)
            base64_bytes = base64.b64encode(image_file.read()).decode('utf-8')
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "Give the which language is precent in image and Extract only the raw text from the image. Do not include any explanations, headers, markdown, or additional comments. Just return the exact text you can read from the image, even if it's partial, blurry, or rotated."},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_bytes}"
                        }},
                    ]}
                ],
                max_tokens=4096
            )
            return response.choices[0].message.content
    except:
        return "OpenAIError"


def extract_text_from_pdf(pdf_path):
    try:
        images = convert_from_path(pdf_path)
        extracted_text = ""
        for i, image in enumerate(images):
            temp_path = f"temp_page_{i}.png"
            image.save(temp_path, "PNG")
            text = extract_text_from_image(temp_path)
            extracted_text += f"\n--- Page {i + 1} ---\n{text}"
            os.remove(temp_path)
        return extracted_text
    except:
        return "PDF_error"


def detect_language(text):
    prompt = f"Detect the language of the following text and reply ONLY with the language name.\n\nText: {text}"
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

def home(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in...!')
        return redirect('index')

    already_filled = SurveyResponse.objects.filter(user=request.user).exists()
    if not already_filled:
        return redirect('survey')
    target_lang = None
    if request.method == 'POST':
        source_lang = request.POST.get('source_language')
        target_lang = request.POST.get('target_language')
        uploaded_file = request.FILES.get('file')
        output_format = request.POST.get('output_format')
        
        if not source_lang or not target_lang:
            messages.error(request, "Please select both source and target languages.")
            return redirect('/home')

        if source_lang == target_lang:
            messages.warning(request, "Source and target languages must be different.")
            return redirect('/home')

        if target_lang not in lang_map:
            messages.error(request, f"Error: Invalid target language '{target_lang}'")
            return redirect('/home')

        if not uploaded_file:
            messages.error(request, "Please upload a file.")
            return redirect('/home')

        delete_all_temp_files()
        file_path = handle_uploaded_temp_file(uploaded_file)

        sub = Subscription.objects.filter(user=request.user, is_active=True).first()
        usage = None
        if sub:
            usage, _ = Usage.objects.get_or_create(subscription=sub)
            total_requests = usage.image_requests_used + usage.pdf_requests_used
            if sub.plan.name == 'basic' and total_requests >= 50:
                messages.error(request, "You have reached your 50 Image/PDF requests limit for the Basic plan. Please upgrade to Pro.")
                return redirect('/home')
            elif sub.plan.name == 'pro' and total_requests >= 300:
                messages.error(request, "You have reached your 300 Image/PDF requests limit for the Pro plan. Please upgrade to Enterprise.")
                return redirect('/home')
        else:
            file_count = Translations.objects.filter(user=request.user).count()
            if file_count >= 5:
                form = UserReviewForm()
                return render(request, "home.html", {'show_subscription_modal': True, 'form': form, 'output': True})

        if file_path.lower().endswith('.pdf'):
            extracted_text =  extract_text_from_pdf(file_path)
            if sub and usage:
                usage.pdf_requests_used += 1
                usage.save()
            # extracted_text = "సీరియారిటీ నైపుణ్యాలు మరియు అభినందనలు!"
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            extracted_text =  extract_text_from_image(file_path)
            if sub and usage:
                usage.image_requests_used += 1
                usage.save()
            # extracted_text = "हिंदी निबंध की आरंभिक परंपरा का निर्माण भारतेंदु युग के लेखकों से हुआ। राष्ट्रीय जागरण, मुद्रण-कला का प्रसार एवं पत्र-पत्रिकाओं का प्रकाशन, गद्य की बढ़ती लोकप्रियता, अँग्रेज़ी साहित्य से संपर्क आदि ने बतौर विधा निबंध-साहित्य के उदय में प्रमुख भूमिका निभाई। विषय, शैली और भाषा में नवीन प्रयोगों के भारतेंदुयुगीन योगदान के बाद भाषा के मानकीकरण, चिंतन की प्रौढ़ता और शैली के परिष्करण के रूप में प्रमुख योगदान द्विवेदीयुगीन निबंधकारों का रहा। हिंदी निबंध-साहित्य में आचार्य रामचंद्र शुक्ल को केंद्रीय महत्त्व प्राप्त है जिन्होंने विचार, भाषा और शैली तीनों ही स्तरों पर इसे उच्चस्तरीय स्वरूप प्रदान किया। आचार्य शुक्ल ने निबंध को गद्य की कसौटी कहा है।"
            # extracted_text = ""
        else:
            messages.error(request,"Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG file only.")
            return redirect("home")
        os.remove(file_path)
        
        if extracted_text == "OpenAIError":
            messages.warning(request,"Service temporarily unavailable!")
            return redirect("home")
        
    
        if extracted_text == "PDF_error":
            messages.warning(request,"The uploaded PDF file is not supported..!")
            return redirect("home")
    
        
        if not extracted_text.strip():
            messages.warning(request, "No text could be extracted from the file. Please try a clearer image or different file.")
            return redirect('/home')
        if output_format == "paragraph":
            if source_lang == "auto":
                auto_language = detect_language(extracted_text)
                source_lang = str(auto_language).lower()
            source_lang_code, source_script = lang_map[source_lang]
            target_lang_code, target_script = lang_map[target_lang]
            target_transliterate = transliterate(extracted_text,source_script,target_script)
            target_meaning = GoogleTranslator(source=source_lang_code, target=target_lang_code).translate(extracted_text)
            
            english_transliterate = transliterate(extracted_text,source_script,IAST)
            english_meaning = GoogleTranslator(source=source_lang_code, target='en').translate(extracted_text)

            output_data = [extracted_text, target_transliterate, target_meaning, english_transliterate, english_meaning]
            df = pd.DataFrame([output_data], columns=[
                "Input Word", 
                f"{target_lang.capitalize()} Transliteration", 
                f"{target_lang.capitalize()} Meaning",
                "English Transliteration",
                "English Meaning"
            ])
            
            output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')
            os.makedirs(output_directory, exist_ok=True)
            csv_file_path = os.path.join(output_directory, 'output.csv')
            df.to_csv(csv_file_path, index=False, encoding="utf-8-sig")
            with open(csv_file_path, 'rb') as f:
                translation_record = Translations(
                    user=request.user,
                    language=source_lang.capitalize(),
                    target_language=target_lang.capitalize()
                )
                translation_record.file = uploaded_file
                translation_record.save()
                output_file_instance = Output_files(
                    translation=translation_record,
                    file=File(f, name='output.csv')
                )
                output_file_instance.save()
            messages.info(request, "Translation completed...!")
            return render(request, 'home.html', {
                'target_transliterate': target_transliterate,
                'target_meaning': target_meaning,
                'english_transliterate':english_transliterate,
                'english_meaning':english_meaning,
                'target_lang': str(target_lang).title(),
                'word_count': len(extracted_text.split()),
                'extracted_text':extracted_text,
                'output_file':output_file_instance,
                'para':True
            })
        else:
            if source_lang == "auto":
                auto_language = detect_language(extracted_text)
                source_lang = str(auto_language).lower()
            extracted_words = extracted_text.split()  # Convert to list of words
            output_data = get_transliterations_chatgpt(extracted_words, source_lang, target_lang)  
            # Expected output_data format: [[word, target_trans, target_mean, eng_trans, eng_mean], ...]

            # Create DataFrame
            df = pd.DataFrame(output_data, columns=[
                "Input Word",
                f"{target_lang.capitalize()} Transliteration",
                f"{target_lang.capitalize()} Meaning",
                "English Transliteration",
                "English Meaning"
            ])

            # Save CSV
            output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')
            os.makedirs(output_directory, exist_ok=True)
            csv_file_path = os.path.join(output_directory, 'output.csv')
            df.to_csv(csv_file_path, index=False, encoding="utf-8-sig")

            # Save records in DB
            with open(csv_file_path, 'rb') as f:
                translation_record = Translations(
                    user=request.user,
                    language=source_lang.capitalize(),
                    target_language=target_lang.capitalize()
                )
                translation_record.file = uploaded_file
                translation_record.save()

                output_file_instance = Output_files(
                    translation=translation_record,
                    file=File(f, name='output.csv')
                )
                output_file_instance.save()

            # Extract separate columns for rendering (optional)
            target_transliterate = [row[1] for row in output_data]
            target_meaning = [row[2] for row in output_data]
            english_transliterate = [row[3] for row in output_data]
            english_meaning = [row[4] for row in output_data]

            messages.info(request, "Translation completed...!")

            return render(request, 'home.html', {
                'target_transliterate': target_transliterate,
                'target_meaning': target_meaning,
                'english_transliterate': english_transliterate,
                'english_meaning': english_meaning,
                'target_lang': str(target_lang).title(),
                'word_count': len(extracted_words),
                'extracted_text': " ".join(extracted_words),
                'output_file': output_file_instance,
                'table_headers': df.columns.tolist(), 
                'table_rows': df.values.tolist()
            })

    form = UserReviewForm()
    output = True
    return render(request, 'home.html', {'form': form,'output':output})



def handle_uploaded_temp_file(uploaded_file):
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    with open(temp_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return temp_path



def save_page_image(pix, page_num):
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_image')
    os.makedirs(temp_dir, exist_ok=True)

    image_path = os.path.join(temp_dir, f"page_{page_num}.jpg")
    pix.save(image_path)
    return image_path



def delete_all_temp_files():
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')


def delete_all_temp_pdf_image_files():
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'pdf_image')
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')



def translations_history(request):
    if not request.user.is_authenticated:
        return redirect('index')
    data = Translations.objects.filter(user=request.user)
    paginator = Paginator(data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "translations_history.html", {'page_obj': page_obj})


def download_csv(request,id):
    try:
        translation = Translations.objects.get(id=id)
        output_file = Output_files.objects.get(translation=translation)
        with open(output_file.file.path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{output_file.file.name.split("/")[-1]}"'
            return response
    except Exception as e:
        messages.error(request,f"{e}")
        return redirect("translations_history")

# User Review code

@login_required
def submit_review(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        review_text = request.POST.get('review_text')
        star_rating = request.POST.get('star_rating')
        if name and review_text and star_rating:
            User_Reviews.objects.create(
                user=request.user,
                name=name,
                review_text=review_text,
                star_rating=int(star_rating)
            )
            return JsonResponse({'success': True})

        return JsonResponse({'success': False, 'error': 'Missing fields'}, status=400)

    return JsonResponse({'error': 'Invalid method'}, status=405)



 

# ===== Error pages ======

def custom_404(request, exception):
    return render(request, '404_error.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)




# ==== Enquiry ====

def pdf_download():
    pdf_path = os.path.join(
            settings.BASE_DIR,
            'static/pdf/Ai_Foundation.pdf'
        )
    return FileResponse(
            open(pdf_path, 'rb'),
            as_attachment=True,
            filename='Ai_Foundation.pdf'
        )


def enquiry_view(request):
    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message_text = request.POST.get('message')

        # Basic backend validation
        if not full_name or not email or not phone:
            messages.error(request, "All required fields must be filled.")
            return redirect('index')

        # Save to DB
        enquiry = ClassInquiry.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            message=message_text
        )

        # Email notification
        subject = "New Class Inquiry Submitted"
        message = (
            f"Hello Admin,\n\n"
            f"You have received a new inquiry.\n\n"
            f"Name: {full_name}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Message: {message_text or 'No message provided'}\n\n"
            f"Submitted on: {enquiry.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )

        # PDF download


        messages.success(
            request,
            "Thank you! Your inquiry has been submitted successfully."
        )

        pdf_download()
        request.session['from_enquiry'] = True
        return redirect('index')


def terms(request):
    return render(request,"terms.html")


def policy(request):
    return render(request,"policy.html")


def refund(request):
    return render(request,"refund.html")


def get_user_active_plan(user):
    if user.is_authenticated:
        sub = Subscription.objects.filter(user=user, is_active=True).first()
        if sub:
            return sub.plan.name
    return None

def basic_plan(request):
    return render(request,"basic_plan.html", {'active_plan': get_user_active_plan(request.user)})

def pro_plan(request):
    return render(request,"pro_plan.html", {'active_plan': get_user_active_plan(request.user)})
    
def enterprise_plan(request):
    return render(request,"enterprise_plan.html", {'active_plan': get_user_active_plan(request.user)})

@login_required
def current_plan_view(request):
    subscription = Subscription.objects.filter(user=request.user, is_active=True).first()
    if not subscription:
        return redirect('basic_plan')
    
    days_left = 0
    if subscription.end_date:
        days_left = (subscription.end_date - timezone.now().date()).days
    
    return render(request, 'current_plan.html', {
        'plan': subscription,
        'expiry_date': subscription.end_date,
        'days_left': days_left
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import Plan, PaymentOrder, UserSubscription
from .utils import initiate_phonepe_payment, verify_payment_status, generate_order_id


# ─────────────────────────────────────────────────────────────
# PLANS PAGE
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
# INITIATE PAYMENT
# ─────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────
# RESULT PAGES
# ─────────────────────────────────────────────────────────────

@login_required
def payment_success_view(request, order_id):
    order = get_object_or_404(PaymentOrder, id=order_id, user=request.user)
    return render(request, 'payments/success.html', {'order': order})


@login_required
def payment_pending_view(request, order_id):
    order = get_object_or_404(PaymentOrder, id=order_id, user=request.user)
    return render(request, 'payments/pending.html', {'order': order})


@login_required
def payment_failed_view(request, order_id):
    order = get_object_or_404(PaymentOrder, id=order_id, user=request.user)
    return render(request, 'payments/failed.html', {'order': order})


@login_required
def dashboard_view(request):
    """User dashboard showing active plan and payment history."""
    subscription = None
    try:
        sub = request.user.payment_subscription   # ← updated
        if sub.is_active():
            subscription = sub
    except UserSubscription.DoesNotExist:
        pass

    payment_history = PaymentOrder.objects.filter(
        user=request.user, status='success'
    ).select_related('plan').order_by('-paid_at')

    return render(request, 'payments/dashboard.html', {
        'subscription': subscription,
        'payment_history': payment_history,
    })


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def chatbots(request):
    icon_status = True
    return render(request,"chatbots.html",{'icon_status':icon_status})





def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)

        user_message = data.get("message")
        bot_type = data.get("bot")

        system_prompts = {
            "careerpilot": "You are a career expert. Help with jobs, interviews, and career guidance.",
            "resumex": "You are a resume expert. Improve resumes and make them ATS-friendly.",
            "assistx": "You are a helpful AI assistant for general tasks."
        }

        system_prompt = system_prompts.get(bot_type, "You are a helpful assistant.")

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )

            reply = response.choices[0].message.content

            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)





import PyPDF2
import docx



@csrf_exempt
def upload_resume(request):
    if request.method == "POST":
        file = request.FILES.get('resume')

        if not file:
            return JsonResponse({"error": "No file uploaded"})

        text = ""

        # ✅ Extract text
        if file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"

        else:
            return JsonResponse({"error": "Unsupported file format"})

        # 🔥 AI Prompt
        prompt = f"""
You are a professional Resume Evaluator AI.

Analyze the following resume and provide:

1. Resume Score (out of 100)
2. Strengths
3. Weaknesses
4. Skill Gap Analysis

Resume:
{text[:4000]}
"""

        try:
            # ✅ Use correct client here
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a resume expert."},
                    {"role": "user", "content": prompt}
                ]
            )

            reply = response.choices[0].message.content

            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


import uuid
from django.shortcuts import render, redirect, reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest

# Initialize PhonePe Client
env_type = Env.PRODUCTION
client = StandardCheckoutClient.get_instance(
    client_id=settings.PHONEPE_CLIENT_ID,
    client_secret=settings.PHONEPE_CLIENT_SECRET,
    client_version=settings.PHONEPE_CLIENT_VERSION,
    env=env_type
)

def init_pay(request):
    return render(request, 'payments/home.html')

def initiate_payment(request):
    if request.method == 'POST':
        plan_name = request.POST.get('plan')
        plan = Plan.objects.get(name=plan_name)
        amount_val = plan.price
        try:
            amount_float = float(amount_val)
            if amount_float <= 0:
                raise ValueError("Amount must be greater than zero.")
            amount_in_paise = int(amount_float * 100)
        except (ValueError, TypeError) as e:
            return render(request, 'payments/error.html', {'error': f'Invalid amount: {str(e)}'})

        order_id = str(uuid.uuid4())
        # Save transaction in DB
        transaction=Transaction.objects.create(
            user=request.user,
            order_id=order_id,
            amount=amount_val,
            status='PENDING'
        )
        Subscription.objects.create(user=request.user,plan=Plan.objects.get(name=plan_name),transaction=transaction)

        # Save order_id in session for redundancy
        request.session['pending_order_id'] = order_id
        
        redirect_url = request.build_absolute_uri(reverse('payment_callback') + f'?merchantOrderId={order_id}')
        
        pay_request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=order_id,
            amount=amount_in_paise,
            redirect_url=redirect_url
        )
        
        try:
            response = client.pay(pay_request)
            return redirect(response.redirect_url)
        except Exception as e:
            # Handle error
            return render(request, 'payments/error.html', {'error': str(e)})
            
    return redirect('init_pay')

@csrf_exempt
def payment_callback(request):
    # Retrieve order_id from query params or session
    order_id = request.GET.get('merchantOrderId') or request.POST.get('merchantOrderId') or request.session.get('pending_order_id')
    
    if not order_id:
        return render(request, 'payments/error.html', {'error': 'Invalid callback: Missing Order ID'})

    try:
        response = client.get_order_status(order_id)
        transaction = Transaction.objects.get(order_id=order_id)
        subscription = Subscription.objects.get(transaction=transaction)
        
        if response.state == 'COMPLETED':
            transaction.status = 'SUCCESS'
            # The SDK v2 returns transaction details in paymentDetails list
            if hasattr(response, 'paymentDetails') and response.paymentDetails:
                transaction.transaction_id = response.paymentDetails[0].transactionId
            transaction.save()
            subscription.is_active = True
            subscription.save()
            return redirect('current_plan')
        elif response.state == 'FAILED':
            transaction.status = 'FAILED'
            transaction.save()
            return render(request, 'payments/failure.html', {'transaction': transaction})
        else:
            return render(request, 'payments/pending.html', {'transaction': transaction})
            
    except Transaction.DoesNotExist:
        return render(request, 'payments/error.html', {'error': 'Transaction not found'})
    except Exception as e:
        return render(request, 'payments/error.html', {'error': str(e)})
