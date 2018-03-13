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

LOGGING['handlers']['sentry'] = {
    'level': 'ERROR',
    'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
}
LOGGING['root']['handlers'].append('sentry')
