# Django Query Logger

[![Build Status](https://travis-ci.org/4word/django-query-logger.svg?branch=master)](https://travis-ci.org/dobarkod/django-query-logger?branch=master)

Query Logger is a Django mixin class for logging duplicate or slow queries, query execution time, 
and total execution time. It's useful for debugging specific areas of your code, and since its a
mixin, it can be added to any class (class based views, django rest framework serializers, celery
tasks, etc), and turned on or off based on any logic.

The logic for detecting duplicate queries and finding long running queries, as well as the 
structure of the project and even this readme, are all inspired by (and in many cases copied over) 
from Django Query Inspector (which unfortunately only works as a middleware, which was not what I needed), 
which can be found here: (https://github.com/dobarkod/django-queryinspect)

Works with Django (1.4, 1.5, 1.6, 1.7, 1.8, 1.9) and Python (2.7, 3.3, 3.4, 3.5).

Example log output:

    [SQL] 17 queries (4 duplicates), 34 ms SQL time, 243 ms total request time

The duplicate queries can also be shown in the log:

    [SQL] repeated query (6x): SELECT "customer_role"."id",
        "customer_role"."contact_id", "customer_role"."name"
        FROM "customer_role" WHERE "customer_role"."contact_id" = ?

The duplicate queries are detected by ignoring any integer values in the SQL
statement. The reasoning is that most of the duplicate queries in Django are
due to results not being cached or pre-fetched properly, so Django needs to
look up related fields afterwards. This lookup is done by the object ID, which
is in most cases an integer.

The heuristic is not 100% precise so it may have some false positives or
negatives, but is a very good starting point for most Django projects.

For each duplicate query, the Python traceback can also be shown, which may
help with identifying why the query has been executed:

    File "/vagrant/api/views.py", line 178, in get
        return self.serialize(self.object_qs)
    File "/vagrant/customer/views.py", line 131, in serialize
        return serialize(objs, include=includes)
    File "/vagrant/customer/serializers.py", line 258, in serialize_contact
        lambda obj: [r.name for r in obj.roles.all()]),
    File "/vagrant/customer/serializers.py", line 258, in <lambda>
        lambda obj: [r.name for r in obj.roles.all()]),

## Quickstart

Install from the Python Package Index:

    pip install django-query-logger

And thats it. You can import the mixin with:

    from query_logger import DatabaseQueryLoggerMixin
    
Any class can start and stop the debugger using the start_query_logging and stop_query_logging
methods. The logs are actually output when you call stop_query_logging.

    class SomeClass(DatabaseQueryLoggerMixin):
        def go_stuff(self):
            self.start_query_logging()
            # ... do some queries
            self.stop_query_logging()
            # ... You can keep doing more stuff, if you want, no more queries will get logged

Add it to any class, such as a Django Rest Framework serializer, and begin using it. You can even
turn it on and off based on your own logic, so it doesnt run all the time:

    from django.core.cache import cache
    from rest_framework import serializers
    from query_logger import DatabaseQueryLoggerMixin
    from .models import MyModel
    
    class MySerializer(serlializers.ModelSerializer, DatabaseQueryLoggerMixin):
        model = MyModel
        
        def save(self, request, *args, **kwargs):
            if cache.get(request.user.id):
                self.start_query_logging()
            # ... stuff happens here, remember to turn it off when your done
            

Update your logging configuration so the output from the query_logger app
shows up:

    LOGGING = {
        ...
        'handlers': {
            ...
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
            ...
        },

        'loggers': {
            ...
            'query_logger': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
        ...
    }

## Configuration

The behaviour of Django Query Logger can be fine-tuned via the following
settings variables:

    LOG_QUERY_DATABASE_CONNECTION = 'default'  # Change this if you want to log from a different db connection
    LOG QUERY_DUPLICATE_QUERIES = True  # Turn this off if you dont want to see duplicate query logs
    LOG_QUERY_TRACEBACKS = False  # Include the traceback in your query logs. Useful if your not sure where 
                                  # queries are coming from. Caution: turning this on everywhere can be a 
                                  # performance issue
    LOG_QUERY_TIME_ABSOLUTE_LIMIT = 1000  # This is the time in milliseconds to log a long running query. 
                                          # Set to 0 for no long running query logging

## Dynamic Configuration

In addition to the settings available above, you can turn these config options on and off at run time. I have
done this to, for example, only turn on tracebacks for a specific user. Just pass an options dict like this
to the start_query_logging() function. Note: not all of these have to be defined, it will fall back on the 
defaults if there is a missing config option.

    configuration_dict = {
        'connection_name': 'default'  # The name of the db connection to log
        'log_duplicate_queries': True  # Log the duplicate SQL queries
        'log_tracebacks': False  # Include the tracebacks for all the queries
        'log_long_running_time': 1000  # Log long running time for this many milliseconds
    }
    self.start_query_logger(configuration_dict)

## Testing

To run tests just use `tox` command (https://pypi.python.org/pypi/tox)

    tox  # for all supported python and django versions

If you need you can run tox just for single environment, f.i.:

    tox -e py27_django17

For available test environments refer to `tox.ini` file.


## License

Copyright (C) 2016. Shopventory Inc and Django Query Logger contributors

Copyright (C) 2014.-2015. Good Code and Django Query Inspector contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
