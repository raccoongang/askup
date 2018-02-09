from .dev import *  # noqa: F401,F403

DATABASES['default'].update({'USER': 'test', 'NAME': 'travis_test_db', 'HOST': 'localhost'})  # noqa: F405

SECRET_KEY = 'KEY'

DEBUG = False
