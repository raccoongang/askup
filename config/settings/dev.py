from .base import * # noqa F403

DEBUG = True

LTI_SSL = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR + "/../dev.log",  # noqa F405
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'logfile']
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': False,
        },
    }
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
    LOGGING['loggers']['django']['handlers'].append('sentry')
    LOGGING['loggers']['django.db.backends']['handlers'].append('sentry')
