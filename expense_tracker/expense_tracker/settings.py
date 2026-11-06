"""
Django settings for expense_tracker project.

Cấu hình Django cho dự án Quản lý Chi tiêu Cá nhân dành cho sinh viên Việt Nam.
"""

from pathlib import Path
import os
import secrets
import sys

from decouple import config

# Thư mục gốc của dự án (expense_tracker)
BASE_DIR = Path(__file__).resolve().parent.parent

# Khóa bí mật và chế độ gỡ lỗi đọc từ .env bằng python-decouple
IS_FROZEN = getattr(sys, 'frozen', False)
if IS_FROZEN:
    DATA_DIR = Path(os.environ['EXPENSE_TRACKER_DATA_DIR'])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    secret_key_file = DATA_DIR / 'secret_key'
    if not secret_key_file.exists():
        secret_key_file.write_text(secrets.token_urlsafe(50), encoding='utf-8')
    default_secret_key = secret_key_file.read_text(encoding='utf-8').strip()
else:
    DATA_DIR = BASE_DIR
    default_secret_key = 'django-insecure-ptit-nhom8-quanlychitieu-2026-secret-key'

SECRET_KEY = config('SECRET_KEY', default=default_secret_key)
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Ứng dụng quản lý thu chi
    'tracker_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware xác thực JWT cho dự án
    'tracker_app.middleware.JWTAuthenticationMiddleware',
]

ROOT_URLCONF = 'expense_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tracker_app.context_processors.notification_context',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

WSGI_APPLICATION = 'expense_tracker.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/
LANGUAGE_CODE = 'vi'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'

# Cấu hình chuyển hướng đăng nhập / đăng xuất
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
