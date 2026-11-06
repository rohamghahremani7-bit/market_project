from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'unsafe-development-key-change-before-deployment')
DEBUG = os.getenv('DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
ALLOWED_HOSTS = [x.strip() for x in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if x.strip()]

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'django_filters',
    'accounts', 'marketdata', 'publishing', 'analyses', 'auditlog_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog_app.middleware.ActivityLogMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'django.template.context_processors.static',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.getenv('DB_NAME', 'marketanalysis_db'),
    'USER': os.getenv('DB_USER', 'marketanalysis_app'),
    'PASSWORD': os.getenv('DB_PASSWORD', ''),
    'HOST': os.getenv('DB_HOST', '127.0.0.1'),
    'PORT': os.getenv('DB_PORT', '5432'),
    'CONN_MAX_AGE': 60,
    'OPTIONS': {'connect_timeout': 10},
}}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

LANGUAGE_CODE = 'fa'
TIME_ZONE = os.getenv('TIME_ZONE', 'Europe/Berlin')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

# تنظیمات امنیتی مناسب توسعه محلی؛ برای استقرار عمومی باید HTTPS فعال شود.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.4-mini')
AI_MAX_CANDLES = int(os.getenv('AI_MAX_CANDLES', '35'))
AI_REQUIRE_ADMIN_APPROVAL = os.getenv('AI_REQUIRE_ADMIN_APPROVAL', 'True').lower() in {'1', 'true', 'yes', 'on'}
MAX_CSV_SIZE_MB = int(os.getenv('MAX_CSV_SIZE_MB', '20'))
MAX_CANDLES_PER_REQUEST = int(os.getenv('MAX_CANDLES_PER_REQUEST', '5000'))
ARTICLE_IMAGE_MAX_MB = 5

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
ARTICLE_REQUIRE_ADMIN_APPROVAL = os.getenv('ARTICLE_REQUIRE_ADMIN_APPROVAL', 'False').lower() in {'1', 'true', 'yes', 'on'}
