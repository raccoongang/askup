# Celery settings
AMQP_USER = 'rabbitmq'
AMQP_PASS = 'rabbitmq'
SUBSCRIPTION_SCHEDULE = {'hour': '9', 'minute': '0', 'day_of_week': '4'}

SERVER_PROTOCOL = 'https'
SERVER_HOSTNAME = 'askup.net'

# SENTRY could contain sentry dsn string or None. If contains a sentry dsn string,
# then all exceptions from the application will be forwarded to this url.
SENTRY_DSN = None

# Email credentials
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'AskUp mailer <mailer@askup.net>'

SECRET_KEY = 'default key'
