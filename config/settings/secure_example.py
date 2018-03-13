# SENTRY could contain sentry dsn string or None/False. If contains a sentry dsn string,
# then all exceptions from the application will be forwarded to this url.
SENTRY = False

# Email credentials
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'AskUp mailer <mailer@askup.net>'

SECRET_KEY = 'default key'
