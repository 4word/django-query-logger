from django.conf import settings
from logging import getLogger

logger = getLogger(__name__)


class DatabaseQueryLoggerMixinConfig(object):
    """
    A config object for making sure we have good defaults in the database query debug mixin. Any of these can be
    overridden by passing in the corresponding kwarg
    """
    def __init__(self, **kwargs):
        self.connection_name = kwargs.get('connection_name',
                                          getattr(settings, 'LOG_QUERY_DATABASE_CONNECTION', 'default'))
        self.log_duplicate_queries = kwargs.get('log_duplicate_queries',
                                                getattr(settings, 'LOG_QUERY_DUPLICATE_QUERIES', True))
        self.log_tracebacks = kwargs.get('log_tracebacks',
                                         getattr(settings, 'LOG_QUERY_TRACEBACKS', False))
        self.log_long_running_time = kwargs.get('log_long_running_time',
                                                getattr(settings, 'LOG_QUERY_TIME_ABSOLUTE_LIMIT', 1000))

        self.logging_extras = kwargs.get('logging_extra_dict', {})

        # This is for internal testing only. If you add unit tests yourself for the query debbuging mixin, then you can
        # define a settings.TESTING variable that is True when unit tests are running.
        self.testing = getattr(settings, 'TESTING', False)
