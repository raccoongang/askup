from .dev import *  # noqa: F401,F403

DATABASES['default']['USER'] = 'test'  # noqa: F405
DATABASES['default']['NAME'] = 'travis_test_db'  # noqa: F405

try:
    import config.settings.secure as secure
except ImportError:
    import config.settings.secure_example as secure
    DATABASES['default']['HOST'] = 'localhost'  # noqa: F405

SECRET_KEY = 'KEY'

DEBUG = False
