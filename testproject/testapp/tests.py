# stdlib
import inspect

# django
from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
try:
    from django.db.backends import util
except ImportError:  # Django changed util to utils at some point
    from django.db.backends import utils as util

# third party
from query_logger import DatabaseQueryLoggerMixin

# project
from .models import Author, Book, Publisher


class DatabaseQueryDebugMixinTest(TestCase, DatabaseQueryLoggerMixin):
    def setUp(self):
        self.author = Author.objects.create(name="John Doe")
        self.publisher = Publisher.objects.create(name="Book Club")

        self.book1 = Book.objects.create(author=self.author, publisher=self.publisher, title="Book1")
        self.book2 = Book.objects.create(author=self.author, publisher=self.publisher, title="Book1")

    def test_monkey_patched_debug_wrapper(self):
        debug_config = {
            'log_tracebacks': True,
            'connection_name': 'default'
        }
        self.start_query_logging(debug_config)
        source = inspect.getsource(util.CursorDebugWrapper.execute)
        self.assertTrue("traceback.extract_stack()" in str(source))
        source = inspect.getsource(util.CursorDebugWrapper.executemany)
        self.assertTrue("traceback.extract_stack()" in str(source))

        self.stop_query_logging()

        source = inspect.getsource(util.CursorDebugWrapper.execute)
        self.assertFalse("traceback.extract_stack()" in str(source))
        source = inspect.getsource(util.CursorDebugWrapper.executemany)
        self.assertFalse("traceback.extract_stack()" in str(source))

    @override_settings(DEBUG=True)
    def test_duplicate_queries_detected(self):
        self.assertTrue(settings.DEBUG)
        self.start_query_logging()
        a = list(Author.objects.filter(id=self.author.id))
        b = list(Book.objects.all())
        c = list(Book.objects.all())
        info_tuple = self.stop_query_logging()
        self.assertEqual(len(info_tuple[0]), 3)  # The first position of the tuple is a list of queries that were run
        self.assertEqual(info_tuple[1], 1)  # the second position of the tuple is how many duplicate queries were run
        self.assertTrue(info_tuple[2] > 0.00001)  # The third position of the tuple is the total run time

        self.start_query_logging()
        d = list(Book.objects.all())
        e = list(Author.objects.all())
        info_tuple = self.stop_query_logging()
        self.assertEqual(len(info_tuple[0]), 2)  # The first position of the tuple is a list of queries that were run
        self.assertEqual(info_tuple[1], 0)  # the second position of the tuple is how many duplicate queries were run
        self.assertTrue(info_tuple[2] > 0.00001)  # The third position of the tuple is the total run time

    @override_settings(DEBUG=False)
    def test_duplicate_queries_detected_with_debug_off(self):
        self.assertFalse(settings.DEBUG)
        self.start_query_logging()
        a = list(Author.objects.filter(id=self.author.id))
        b = list(Book.objects.all())
        c = list(Book.objects.all())
        info_tuple = self.stop_query_logging()
        self.assertEqual(len(info_tuple[0]), 3)  # The first position of the tuple is a list of queries that were run
        self.assertEqual(info_tuple[1], 1)  # the second position of the tuple is how many duplicate queries were run
        self.assertTrue(info_tuple[2] > 0.00001)  # The third position of the tuple is the total run time

        self.start_query_logging()
        d = list(Book.objects.all())
        e = list(Author.objects.all())
        info_tuple = self.stop_query_logging()
        self.assertEqual(len(info_tuple[0]), 2)  # The first position of the tuple is a list of queries that were run
        self.assertEqual(info_tuple[1], 0)  # the second position of the tuple is how many duplicate queries were run
        self.assertTrue(info_tuple[2] > 0.00001)  # The third position of the tuple is the total run time
