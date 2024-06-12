"""
Django settings for node project.

Generated by 'django-admin startproject' using Django 5.0.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from utilities import utils

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_UPLOAD_MAX_MEMORY_SIZE = (52428800)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-!)*%l&@5szqtcshyzc=aslg36n6b$w3$k9la424&9tzzt^tmxv'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'node',
    'rest_framework',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'node.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'node.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


DATA_PATH = os.environ.get('data_path', './')

PATHS_CONFIG = utils.load_config(os.path.join(DATA_PATH, 'data/config/paths.cnf'), 
                                 [
                                     'mysql',
                                     'rebbit',
                                     'cdn_template_upload_path',
                                     'ca_certificate',
                                     'django_log',
                                     'cdn_template_download_path',
                                     'cdn_result_upload_path',
                                     'cdn_result_download_path',
                                     'image_path',
                                     'source_path',
                                     'preview_source_path',
                                     'thumb_path',
                                     'faces_path',
                                     'result_path',
                                     'watermark_path'
                                ])


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': os.path.join(DATA_PATH, PATHS_CONFIG['mysql']),
            'ssl': {
                'ca': os.path.join(DATA_PATH, PATHS_CONFIG['ca_certificate']),
            },
            'charset': 'utf8mb4',
        }
    }
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REBBIT = os.path.join(DATA_PATH, PATHS_CONFIG['rebbit'])  # Replace with your actual path


CDN_TEMPLATE_UPLOAD_PATH = PATHS_CONFIG['cdn_template_upload_path']
CDN_TEMPLATE_DOWNLOAD_PATH = PATHS_CONFIG['cdn_template_download_path']

CDN_RESULT_UPLOAD_PATH = PATHS_CONFIG['cdn_result_upload_path']
CDN_RESULT_DOWNLOAD_PATH = PATHS_CONFIG['cdn_result_download_path']


IMAGES_PATH = PATHS_CONFIG['image_path']
os.makedirs(IMAGES_PATH, exist_ok=True)

SOURCE_PATH = PATHS_CONFIG['source_path']
os.makedirs(SOURCE_PATH, exist_ok=True)

PREVIEW_SOURCE_PATH = PATHS_CONFIG['preview_source_path']
os.makedirs(PREVIEW_SOURCE_PATH, exist_ok=True)

THUMB_PATH = PATHS_CONFIG['thumb_path']
os.makedirs(THUMB_PATH, exist_ok=True)

FACES_PATH = PATHS_CONFIG['faces_path']
os.makedirs(FACES_PATH, exist_ok=True)

RESULT_PATH = PATHS_CONFIG['result_path']
os.makedirs(RESULT_PATH, exist_ok=True)

WATERMARK_PATH = os.path.join(DATA_PATH, PATHS_CONFIG['watermark_path'])
os.makedirs(os.path.dirname(WATERMARK_PATH), exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": os.path.join(DATA_PATH, PATHS_CONFIG['django_log']),
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

