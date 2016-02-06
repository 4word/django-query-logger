#!/usr/bin/env python

from setuptools import setup, find_packages, Command
import os
import sys


class BaseCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class TestCommand(BaseCommand):

    description = "run self-tests"

    def run(self):
        os.chdir('testproject')
        ret = os.system('%s manage.py test testapp' % sys.executable)
        if ret != 0:
            sys.exit(-1)

setup(
    name='django-query-logger',
    version='0.1.0',
    author='Titus Peterson',
    description='Django Query Logger',
    license='MIT',
    url='https://github.com/4word/django-query-logger',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    install_requires=['Django>=1.4'],
    cmdclass={
        'test': TestCommand,
    }
)
