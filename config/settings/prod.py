from .base import * # noqa F403


DEBUG = False
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'logfile': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR + "/../error.log", # noqa F405
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'logfile']
    },
}

if SENTRY_DSN:  # noqa F405
    INSTALLED_APPS.append('raven.contrib.django.raven_compat')  # noqa F405
    RAVEN_CONFIG = {
        'dsn': SENTRY_DSN,  # noqa F405
    }
    LOGGING['handlers']['sentry'] = {
        'level': 'ERROR',
        'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
    }
    LOGGING['root']['handlers'].append('sentry')
