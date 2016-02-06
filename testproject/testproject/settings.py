# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

sys.path.insert(0, os.path.dirname(BASE_DIR))

SECRET_KEY = 'pf87b=3sm!abi6dbt3b8b3hw$yqp4^7#f*87&l2r7tr2qx2_@s'
DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = (
    'testapp',
)

ROOT_URLCONF = 'testproject.urls'
WSGI_APPLICATION = 'testproject.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = '/static/'

LOG_QUERY_DATABASE_CONNECTION = 'default'
LOG_QUERY_DUPLICATE_QUERIES = True
LOG_QUERY_TRACEBACKS = False
LOG_QUERY_TIME_ABSOLUTE_LIMIT = 100

TESTING = 'test' in sys.argv

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'memory': {
            'level': 'DEBUG',
            'class': 'testapp.memorylog.MemoryHandler',
        },
    },
    'loggers': {
        'query_logger': {
            'handlers': ['memory'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
