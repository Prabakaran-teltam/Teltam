from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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
import easyocr
import cv2
from googletrans import Translator
from indic_transliteration.sanscript import transliterate, IAST, ITRANS
from indic_transliteration import sanscript
import os
import pandas as pd
from .models import *
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.files import File
import fitz
from PIL import Image
import numpy as np
import shutil
from ocr_tamil.ocr import OCR as tamil_OCR
from django.core.mail import EmailMultiAlternatives




def index(request):
    img = Translations.objects.all().count()
    clients = User.objects.all().count
    reviews = User_Reviews.objects.filter(star_rating=5)[:6]
 
    return render(request,'index.html',{'img':img,'clients':clients,'reviews':reviews})



def log_in(request):
    error_message = None
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get("username")
        pws = request.POST.get("password")
        user = authenticate(request, username=name, password=pws)
        if user is not None:
            login(request, user)
            messages.success(request,f"Welcome back to Teltam {request.user}...!")
            return redirect('survey')
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
}


def preprocess_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def translate_to_tamil(word):
    translator = Translator()
    return translator.translate(word, src="hi", dest="ta").text

# Edited
def get_transliterations(words, source_language, target_language):
 
    translator = Translator()
    
    source_lang_code, source_script = lang_map[source_language]
    target_lang_code, target_script = lang_map[target_language]

    output_data = []
    paragraph_data = []
    for word in words:
        try:
            target_transliteration = transliterate(word, source_script, target_script)
            target_meaning = translator.translate(word, src=source_lang_code, dest=target_lang_code).text
            english_transliteration = transliterate(word, source_script, IAST) 
            english_meaning = translator.translate(word, src=source_lang_code, dest="en").text
            output_data.append([word, target_transliteration, target_meaning, english_transliteration, english_meaning])
        except Exception as e:
            # print(f"Error with '{word}': {e}")
            output_data.append([word, None, None,None, None])
    # word = ' '.join(words)
    # target_transliteration = transliterate(word, source_script, target_script)
    # target_meaning = translator.translate(word, src=source_lang_code, dest=target_lang_code).text
    # english_transliteration = transliterate(word, source_script, ITRANS)
    # print("=========================",source_lang_code)
    # english_meaning = translator.translate(word, src=source_lang_code, dest="en").text
    # paragraph_data.append([word, target_transliteration, target_meaning, english_transliteration, english_meaning])
    paragraph_data = None
    return output_data, paragraph_data




def home(request):
    """
    View function for the home page that handles file uploads and translation.
    Requires authentication and processes OCR and translation for uploaded files.
    """
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in...!')
        return redirect('index')

    already_filled = SurveyResponse.objects.filter(user=request.user).exists()
    if not already_filled:
        return redirect('survey')

    output_data = []
    target_lang = None

    if request.method == 'POST':
        try:
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
            
            if source_lang == 'tamil':
                messages.error(request,"Currently unavailable on the server")
            
            if source_lang != 'tamil':
                tesseract_lang, _ = lang_map[source_lang]

            delete_all_temp_files()
            file_path = handle_uploaded_temp_file(uploaded_file)

            if not file_path or not os.path.exists(file_path):
                messages.error(request, "Error processing uploaded file.")
                return redirect('/home')

            extracted_text = ""

            if file_path.lower().endswith('.pdf'):
                try:
                    pdf_doc = fitz.open(file_path)
                    if len(pdf_doc) == 0:
                        messages.error(request, "The PDF file appears to be empty.")
                        return redirect('/home')

                    if source_lang.lower() == "tamil":
                        tamil_ocr = tamil_OCR(detect=True)
                        for page_num in range(len(pdf_doc)):
                            try:
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap(dpi=300)
                                image_path = save_page_image(pix, page_num)
                                result = tamil_ocr.predict(image_path)
                                page_text = " ".join(result[0]) if result and result[0] else ""
                                extracted_text += page_text + " "
                                # print(f"[Tamil OCR] Page {page_num+1}: {page_text[:100]}...")
                            except Exception as e:
                                messages.warning(request, f"Error processing page {page_num+1}: {str(e)}")
                        delete_all_temp_pdf_image_files()

                    else:
                        reader = easyocr.Reader([tesseract_lang], gpu=False)
                        for page_num in range(len(pdf_doc)):
                            try:
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap(dpi=300)
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                img_np = np.array(img.convert("RGB"))
                                result = reader.readtext(img_np)
                                page_text = ' '.join([item[1] for item in result]) if result else ""
                                extracted_text += page_text + " "
                                # print(f"[EasyOCR] Page {page_num+1}: {page_text[:100]}...")
                            except Exception as e:
                                messages.warning(request, f"Error processing page {page_num+1}: {str(e)}")

                    pdf_doc.close()

                except fitz.FileDataError:
                    messages.error(request, "Invalid or corrupted PDF file.")
                    return redirect('/home')
                except Exception as e:
                    messages.error(request, f"Error processing PDF: {str(e)}")
                    return redirect('/home')

            else:
                try:
                    preprocessed_image = preprocess_image(file_path)
                    if source_lang.lower() == "tamil":
                        tamil_ocr = tamil_OCR(detect=True)
                        result = tamil_ocr.predict(preprocessed_image)
                        extracted_text = " ".join(result[0]) if result and result[0] else ""
                        # print(f"[Tamil OCR] Image text: {extracted_text[:100]}...")
                    else:
                        reader = easyocr.Reader([tesseract_lang], gpu=False)
                        result = reader.readtext(preprocessed_image)
                        extracted_text = ' '.join([item[1] for item in result]) if result else ""
                        # print(f"[EasyOCR] Image text: {extracted_text[:100]}...")

                except Exception as e:
                    messages.error(request, f"Error processing image: {str(e)}")
                    return redirect('/home')

            if not extracted_text.strip():
                messages.warning(request, "No text could be extracted from the file. Please try a clearer image or different file.")
                return redirect('/home')

            words = extracted_text.split()
            if not words:
                messages.warning(request, "No words were found in the extracted text.")
                return redirect('/home')

            try:
                output_data, paragrph_data = get_transliterations(words, source_lang, target_lang)
                if not output_data:
                    messages.warning(request, "Translation service could not process the extracted text.")
                    return redirect('/home')

                df = pd.DataFrame(output_data, columns=[
                    "Input Word", 
                    f"{target_lang.capitalize()} Transliteration", 
                    f"{target_lang.capitalize()} Meaning",
                    "English Transliteration",
                    "English Meaning"
                ])

                output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')
                os.makedirs(output_directory, exist_ok=True)
                csv_file_path = os.path.join(output_directory, 'output.csv')

                try:
                    df.to_csv(csv_file_path, index=False, encoding="utf-8-sig")
                except PermissionError:
                    messages.error(request, "Permission denied when saving output file.")
                    return redirect('/home')
                except Exception as e:
                    messages.error(request, f"Error saving output file: {str(e)}")
                    return redirect('/home')

                try:
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
                except (IOError, OSError) as e:
                    messages.error(request, f"Error saving translation record: {str(e)}")
                    return redirect('/home')

                target_lang = target_lang.capitalize()
                messages.info(request, "Translation completed...!")
                # print("====================Output data", output_data)
                return render(request, 'home.html', {
                    'output_data': output_data,
                    'paragrph_data': paragrph_data,
                    'target_lang': target_lang,
                    'word_count': len(output_data)
                })

            except Exception as e:
                messages.error(request, f"Translation error: {str(e)}")
                return redirect('/home')

        except MemoryError:
            messages.error(request, "Server ran out of memory while processing the file.")
            return redirect('/home')
        except TimeoutError:
            messages.error(request, "The server timed out. Please try with a smaller file.")
            return redirect('/home')
        except Exception as e:
            # import traceback
            # print(f"Unexpected server error: {traceback.format_exc()}")
            messages.error(request, f"Unexpected server error: {str(e)}")
            return redirect('/home')

    form = UserReviewForm()
    return render(request, 'home.html', {'form': form})




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
