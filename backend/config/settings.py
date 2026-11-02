from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'users',
    'resources',
    'bookings',
]

AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': config.int('JWT_ACCESS_LIFETIME_MINUTES', default=15) * 60,
    'REFRESH_TOKEN_LIFETIME': config.int('JWT_REFRESH_LIFETIME_DAYS', default=7) * 24 * 60 * 60,
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='booking'),
        'USER': config('DB_USER', default='booking'),
        'PASSWORD': config('DB_PASSWORD', default='booking'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

STATIC_URL = 'static/'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
