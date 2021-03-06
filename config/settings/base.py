"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'debug_toolbar',
    'askup',
    'askup_lti',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'askup.context_processors.notifications_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'askup',
        'USER': 'postgres',
        'PASSWORD': 'pass',
        'HOST': 'postgres',
        'PORT': '5432',
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
        'TIMEOUT': 7 * 24 * 60 * 60,  # default cache timeout set for a week
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = './askup/static'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

INTERNAL_IPS = [
    '127.0.0.1',
    '127.0.1.1',
]

LOGIN_URL = '/askup/sign-in'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Processing the secure settings below
try:
    import config.settings.secure as secure
except ImportError:
    import config.settings.secure_example as secure

SENTRY_DSN = getattr(secure, 'SENTRY_DSN', False)
EMAIL_HOST = secure.EMAIL_HOST
EMAIL_PORT = secure.EMAIL_PORT
EMAIL_HOST_USER = secure.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = secure.EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = secure.EMAIL_USE_TLS
DEFAULT_FROM_EMAIL = secure.DEFAULT_FROM_EMAIL
SECRET_KEY = secure.SECRET_KEY
SERVER_PROTOCOL = secure.SERVER_PROTOCOL
SERVER_HOSTNAME = secure.SERVER_HOSTNAME

# Celery settings
AMQP_USER = secure.AMQP_USER
AMQP_PASS = secure.AMQP_PASS

CELERY_BROKER_URL = 'amqp://{}:{}@rabbitmq:5672//'.format(AMQP_USER, AMQP_PASS)
SUBSCRIPTION_SCHEDULE = secure.SUBSCRIPTION_SCHEDULE

# LTI Parameters
X_FRAME_OPTIONS = "ALLOW"

# SSL proxy fix
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
