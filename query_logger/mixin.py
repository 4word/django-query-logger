# std lib
import collections
import time
import traceback
import re
from logging import getLogger

# django
from django.db import connections
try:
    from django.db.backends.util import CursorDebugWrapper
except ImportError:
    from django.db.backends.utils import CursorDebugWrapper

# project
from .config import DatabaseQueryLoggerMixinConfig

logger = getLogger(__name__)


class DatabaseQueryLoggerMixin(object):
    """
    A mixin for dealing with query debugging.

    Much of the query duplicate and runtime calculation part of this is shamelessly stolen from
    github.com/dobarkod/django-queryinspect and simply updated to work outside of the middleware and instead work
    anywhere that it is turned on.
    """

    # Leave these here so we can unpatch the query wrapper
    REAL_EXEC = CursorDebugWrapper.execute
    REAL_EXEC_MANY = CursorDebugWrapper.executemany

    sql_id_pattern = re.compile(r'=\s*\d+')

    @staticmethod
    def _enable_query_debugging(con_name):
        """
        Alters the debug cursor setting in the Django DB object. Will force any new cursors to use the debug wrapper

        :return:
        """
        if hasattr(connections[con_name], 'use_debug_cursor'):
            connections[con_name].use_debug_cursor = True
        else:
            connections[con_name].force_debug_cursor = True

    @staticmethod
    def _disable_query_debugging(con_name):
        """
        Alters the debug cursor setting in the Django DB object. Will return the cursor wrapper back to the default
        (which may, in fact, actually be the debug cursor already, if settings.DEBUG is True)

        :param con_name:
        :return:
        """
        if hasattr(connections[con_name], 'use_debug_cursor'):
            connections[con_name].use_debug_cursor = False
        else:
            connections[con_name].force_debug_cursor = False

    class QueryInfo(object):
        """
        Basic object for storing query facts
        """
        __slots__ = ('sql', 'time', 'tb')

    @classmethod
    def patch_cursor(cls):
        """
        When tracebacks are turned on, this monkey patches the debug cursor wrapper so we get the current stack trace on
        each execution.

        PROCEED WITH CAUTION.

        This causes significant overhead and should only be turned on when troubleshooting an issue that cannot be
        easily solved in any other way.

        :return:
        """

        def should_include(path):
            if path == __file__ or path + 'c' == __file__:
                return False
            return True

        def tb_wrap(fn):
            def wrapper(self, *args, **kwargs):
                try:
                    return fn(self, *args, **kwargs)
                finally:
                    if hasattr(self.db, 'queries'):
                        tb = traceback.extract_stack()
                        tb = [f for f in tb if should_include(f[0])]
                        self.db.queries[-1]['tb'] = tb

            return wrapper

        CursorDebugWrapper.execute = tb_wrap(cls.REAL_EXEC)
        CursorDebugWrapper.executemany = tb_wrap(cls.REAL_EXEC_MANY)

    @classmethod
    def un_patch_cursor(cls):
        """
        When we have tracebacks on and we stop the debugging, this will un patch the debug cursor so it stops producing
        stack traces at each frame / execution

        :return:
        """

        CursorDebugWrapper.execute = cls.REAL_EXEC
        CursorDebugWrapper.executemany = cls.REAL_EXEC_MANY

    @classmethod
    def get_query_infos(cls, queries):
        """
        Coerces the list of queries in Django DB object into QueryInfo objects for processing.

        :param queries:
        :return:
        """
        retval = []
        for q in queries:
            qi = cls.QueryInfo()
            qi.sql = cls.sql_id_pattern.sub('= ?', q['sql'])
            qi.time = float(q['time'])
            qi.tb = q.get('tb')
            retval.append(qi)
        return retval

    @staticmethod
    def count_duplicates(infos):
        """
        Does basic string comparisons to get the number of duplicate queries.

        :param infos:
        :return:
        """
        buf = collections.defaultdict(lambda: 0)
        for qi in infos:
            buf[qi.sql] += 1
        return sorted(buf.items(), key=lambda el: el[1], reverse=True)

    @staticmethod
    def group_queries(infos):
        """
        Groups queries together by SQL. This is separate from the counted duplicates so we can access the stack trace if
        tracebacks are turned on.

        :param infos:
        :return:
        """
        buf = collections.defaultdict(lambda: [])
        for qi in infos:
            buf[qi.sql].append(qi)
        return buf

    def check_duplicates(self, infos, log_duplicates, log_tracebacks):
        """
        Counts and groups queries and then logs out any duplicates that are found.

        :param infos:
        :param log_duplicates:
        :param log_tracebacks:
        :return:
        """
        duplicates = [(qi, num) for qi, num in self.__class__.count_duplicates(infos) if num > 1]
        duplicates.reverse()
        n = 0
        if len(duplicates) > 0:
            n = (sum(num for qi, num in duplicates) - len(duplicates))

        dup_groups = self.__class__.group_queries(infos)

        if log_duplicates:
            for sql, num in duplicates:
                if log_tracebacks and dup_groups[sql]:
                    extra = {'traceback': ''.join(traceback.format_list(dup_groups[sql][0].tb)),
                             'num': num,
                             'sql': sql,
                             'class_name': self.__class__.__name__,
                             'logtype': 'querylog__duplicate'}
                    for k in self.query_debug_cfg.logging_extras.keys():
                        extra[k] = self.query_debug_cfg.logging_extras[k]
                    logger.warning('[SQL] repeated query (%dx): %s' % (num, sql),
                                   extra=extra)
                else:
                    extra = {'num': num,
                             'sql': sql,
                             'class_name': self.__class__.__name__,
                             'logtype': 'querylog__duplicate'}
                    for k in self.query_debug_cfg.logging_extras.keys():
                        extra[k] = self.query_debug_cfg.logging_extras[k]
                    logger.warning('[SQL] repeated query (%dx): %s' % (num, sql),
                                   extra=extra)
        return n

    def check_absolute_limit(self, infos, log_long_running_time):
        """
        Checks the total SQL running time of each query and, if the running time in ms is longer than the configured
        long running time, logs out the sql and the run time.

        :param infos:
        :param log_long_running_time:
        :return:
        """
        n = len(infos)
        if not log_long_running_time or n == 0:
            return
        elif log_long_running_time > 0:

            query_limit = log_long_running_time / 1000.0

            for qi in infos:
                if qi.time > query_limit:
                    extra = {
                        'class_name': self.__class__.__name__,
                        'time': qi.time * 1000,
                        'limit': query_limit * 1000,
                        'sql': qi.sql,
                        'logtype': 'querylog__longrunning'
                    }
                    for k in self.query_debug_cfg.logging_extras.keys():
                        extra[k] = self.query_debug_cfg.logging_extras[k]
                    logger.warning('[SQL] query execution of %d ms over absolute '
                                   'limit of %d ms: %s' % (
                                       qi.time * 1000,
                                       query_limit * 1000,
                                       qi.sql),
                                   extra=extra
                                   )

    def output_stats(self, infos, num_duplicates, total_time):
        """
        Logs out the summary stats when the debugging is turned off.

        :param infos:
        :param num_duplicates:
        :param total_time:
        :return:
        """
        sql_time = sum(qi.time for qi in infos)
        n = len(infos)

        extra = {
            'class_name': self.__class__.__name__,
            'num': num_duplicates,
            'sqltime': sql_time,
            'totaltime': total_time,
            'logtype': 'querylog__summary'
        }

        for k in self.query_debug_cfg.logging_extras.keys():
            extra[k] = self.query_debug_cfg.logging_extras[k]

        logger.info(
            '[SQL] %d queries (%d duplicates), %d ms SQL time, %d ms total processing time' % (
                n,
                num_duplicates,
                sql_time * 1000,
                total_time * 1000),
            extra=extra
        )

    def start_query_logging(self, config_opts=None):
        """
        The main entry point. Turns on the debug query wrapper and loads the config options from the config_opts
        argument. Will also call the patch for the debug cursor when tracebacks are configured to True.

        :param config_opts:
        :return:
        """
        config_opts = dict() if not config_opts else config_opts
        self.query_debug_cfg = DatabaseQueryLoggerMixinConfig(**config_opts)

        if self.query_debug_cfg.connection_name in connections:
            DatabaseQueryLoggerMixin._enable_query_debugging(self.query_debug_cfg.connection_name)

            self.start_query_debug_time = time.time()
            self.conn_queries_len = len(connections[self.query_debug_cfg.connection_name].queries)

            if self.query_debug_cfg.log_tracebacks:
                self.patch_cursor()

    def stop_query_logging(self):
        """
        Turns off the query debugging and processes the stats collected.
        :return:
        """
        if not hasattr(self, "start_query_debug_time") or self.query_debug_cfg.connection_name not in connections:
            return

        total_time = time.time() - self.start_query_debug_time

        infos = self.get_query_infos(
            connections[self.query_debug_cfg.connection_name].queries[self.conn_queries_len:])

        num_duplicates = self.check_duplicates(infos, self.query_debug_cfg.log_duplicate_queries,
                                               self.query_debug_cfg.log_tracebacks)
        self.check_absolute_limit(infos, self.query_debug_cfg.log_long_running_time)
        self.output_stats(infos, num_duplicates, total_time)

        DatabaseQueryLoggerMixin._disable_query_debugging(self.query_debug_cfg.connection_name)

        # We need to unpatch the debug cursor wrapper otherwise it will keep making stack traces for any queries in it's
        # thread / process until it is stopped.
        if self.query_debug_cfg.log_tracebacks:
            self.un_patch_cursor()

        if self.query_debug_cfg.testing:
            delattr(self, 'query_debug_cfg')    # Lets free this up manually, don't want it sticking around in the
                                                # mixin'ed class in case debugging gets turned back on later in the
                                                # class' execution path
            return infos, num_duplicates, total_time
        else:
            delattr(self, 'query_debug_cfg')    # See comment directly above
            return
