
from pathlib import Path
import os
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from decouple import config
BASE_DIR = Path(__file__).resolve().parent.parent


DEBUG = config('DEBUG', default=True, cast=bool)
SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main",
    "admin_dashboard",
    "widget_tweaks",
    "django_celery_beat",
    "django_ckeditor_5",
    "captcha"
]


RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY')

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "main.middleware.Custom500Middleware"
]

ROOT_URLCONF = "Translater.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR,'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'admin_dashboard.context_processors.notification_count',
            ],
        },
    },
]


WSGI_APPLICATION = "Translater.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

LOGIN_URL = 'login'

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"
CELERY_TIMEZONE = 'Asia/Kolkata'
USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATICFILES_DIRS = [
os.path.join(BASE_DIR, 'static'),
]

# STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles')

MEDIA_URL = '/media/'
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CKEDITOR_5_UPLOAD_FILE_TYPES = ['jpeg', 'png', 'jpg']

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "underline", "strikethrough", "code", "|",
            "subscript", "superscript", "|",
            "link", "imageUpload", "mediaEmbed", "|",
            "bulletedList", "numberedList", "todoList", "|",
            "outdent", "indent", "|",
            "alignment", "blockQuote", "codeBlock", "|",
            "insertTable", "horizontalLine", "pageBreak", "|",
            "undo", "redo", "|",
            "sourceEditing", "selectAll", "findAndReplace", "removeFormat"
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative", "|",
                "imageStyle:alignLeft", 
                "imageStyle:alignCenter", 
                "imageStyle:alignRight", "|",
                "toggleImageCaption", "resizeImage"
            ]
        },
        "table": {
            "contentToolbar": [
                "tableColumn", "tableRow", "mergeTableCells", 
                "tableProperties", "tableCellProperties"
            ]
        },
        "height": 500,
        "width": "100%",
    }
}




EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'teltam2025@gmail.com'
EMAIL_HOST_PASSWORD = 'gvns fnbn hrwd gzgx' 
DEFAULT_FROM_EMAIL = 'webmaster@localhost'



# JAZZMIN_SETTINGS = {
#     "site_header": "Teltam", 
#     "site_title": "Teltam", 
#     "welcome_sign": "Welcome to Teltam Admin!", 
#     "show_ui_builder": False, 
#     "copyright" : "Teltam",
#     "login_logo": None,
#     "site_icon": None,
#     "site_brand": "Teltam",
# }

