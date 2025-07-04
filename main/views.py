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
from indic_transliteration.sanscript import transliterate
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

# POPPLER_PATH = "C:\Release-24.08.0-0\poppler-24.08.0\Library\bin"
# POPPLER_PATH = ""

api_key = config('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

def index(request):
    img = Translations.objects.all().count()
    clients = User.objects.all().count
    reviews = User_Reviews.objects.filter(star_rating=5)[:6]
    blog = BlogPost.objects.filter(status="published")[:3]
    video = Video.objects.filter(is_active=True)
    update_scheduled_posts()
    form = ContactForm()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent. Thank you!")
            return redirect('index')
        else:
            messages.error(request,"Invalid Captcha.")
            return redirect('index')
    return render(request,'index.html',{'img':img,'clients':clients,'reviews':reviews,'blog':blog,'form':form,'video':video})


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
    return render(request,"list_of_blogs.html",{'blogs':blogs,'categories':categories})



def list_of_videos(request):
    videos = Video.objects.filter(is_active=True).order_by('-created_at')
    return render(request,"list_of_videos.html",{'videos':videos})


def tag_based_search(request,tag):
    tag = Tag.objects.get(name=tag)
    blogs = BlogPost.objects.filter(tags=tag)
    return render(request,"list_of_blogs.html",{"blogs":blogs})


def about_us(reqeust):
    return render(reqeust,"about_us.html")


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
                login(request,user)
                messages.success(request, 'Registration successful and verified.')
                return redirect('survey')
            else:
                messages.error(request,'Invalid OTP')
                return redirect('verify_otp')
    else:
        form = OTPForm()
    return render(request,'verify_otp.html',{'form':form})


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

def get_transliterations(words, source_language, target_language):
    source_lang_code, source_script = lang_map[source_language]
    target_lang_code, target_script = lang_map[target_language]
    
    output_data = []

    for word in words:
        try:
            print(f"Processing word: {word}")
            
            # Transliteration to target script
            target_transliteration = transliterate(word, source_script, target_script)
            print(f"Target transliteration: {target_transliteration}")
            
            # Meaning in target language
            target_meaning = GoogleTranslator(source=source_lang_code, target=target_lang_code).translate(word)
            print(f"Target meaning: {target_meaning}")
            
            # Transliteration to English (IAST)
            english_transliteration = transliterate(word, source_script, sanscript.IAST)
            print(f"English transliteration: {english_transliteration}")
            
            # Meaning in English
            english_meaning = GoogleTranslator(source=source_lang_code, target='en').translate(word)
            print(f"English meaning: {english_meaning}")
            
            output_data.append([
                word,
                target_transliteration,
                target_meaning,
                english_transliteration,
                english_meaning
            ])
        except Exception as e:
            print(f"Error with '{word}': {e}")
            output_data.append([word, None, None, None, None])
    
    return output_data, None

# Translater with using Chat GPT API key

def extract_text_from_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            base64_bytes = base64.b64encode(image_file.read()).decode('utf-8')
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extract all text from this image with high accuracy."},
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
    images = convert_from_path(pdf_path)
    extracted_text = ""
    for i, image in enumerate(images):
        temp_path = f"temp_page_{i}.png"
        image.save(temp_path, "PNG")
        text = extract_text_from_image(temp_path)
        extracted_text += f"\n--- Page {i + 1} ---\n{text}"
        os.remove(temp_path)
    return extracted_text


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

        if file_path.lower().endswith('.pdf'):
            extracted_text =  extract_text_from_pdf(file_path)
            # extracted_text = "సీరియారిటీ నైపుణ్యాలు మరియు అభినందనలు!"
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            extracted_text =  extract_text_from_image(file_path)
            # extracted_text = "हिंदी निबंध की आरंभिक परंपरा का निर्माण भारतेंदु युग के लेखकों से हुआ। राष्ट्रीय जागरण, मुद्रण-कला का प्रसार एवं पत्र-पत्रिकाओं का प्रकाशन, गद्य की बढ़ती लोकप्रियता, अँग्रेज़ी साहित्य से संपर्क आदि ने बतौर विधा निबंध-साहित्य के उदय में प्रमुख भूमिका निभाई। विषय, शैली और भाषा में नवीन प्रयोगों के भारतेंदुयुगीन योगदान के बाद भाषा के मानकीकरण, चिंतन की प्रौढ़ता और शैली के परिष्करण के रूप में प्रमुख योगदान द्विवेदीयुगीन निबंधकारों का रहा। हिंदी निबंध-साहित्य में आचार्य रामचंद्र शुक्ल को केंद्रीय महत्त्व प्राप्त है जिन्होंने विचार, भाषा और शैली तीनों ही स्तरों पर इसे उच्चस्तरीय स्वरूप प्रदान किया। आचार्य शुक्ल ने निबंध को गद्य की कसौटी कहा है।"
            # extracted_text = ""
        else:
            messages.error(request,"Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG file only.")
            return redirect("home")
        os.remove(file_path)
        
        if extracted_text == "OpenAIError":
            messages.warning(request,"Service temporarily unavailable!")
            return redirect("home")
        if not extracted_text.strip():
            messages.warning(request, "No text could be extracted from the file. Please try a clearer image or different file.")
            return redirect('/home')
        source_lang_code, source_script = lang_map[source_lang]
        target_lang_code, target_script = lang_map[target_lang]
        target_transliterate = transliterate(extracted_text,source_script,target_script)
        target_meaning = GoogleTranslator(source=source_lang_code, target=target_lang_code).translate(extracted_text)
        print("==========target_transliterate",target_transliterate)
        print("==========target_meaning",target_meaning)

        # Create PDF in memory
        output_data = [extracted_text, target_transliterate, target_meaning]
        df = pd.DataFrame([output_data], columns=[
            "Input Word", 
            f"{target_lang.capitalize()} Transliteration", 
            f"{target_lang.capitalize()} Meaning",
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
            'target_lang': str(target_lang).title(),
            'word_count': len(extracted_text),
            'extracted_text':extracted_text
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
