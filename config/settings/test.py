from .dev import *  # noqa: F401,F403

DATABASES['default']['USER'] = 'test'  # noqa: F405
DATABASES['default']['NAME'] = 'travis_test_db'  # noqa: F405
DATABASES['default']['HOST'] = 'localhost'  # noqa: F405

SECRET_KEY = 'KEY'

DEBUG = False
