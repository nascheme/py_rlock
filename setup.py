#!/usr/bin/env python3

from setuptools import setup, Extension

kw = dict(
    name="rlock_test",
    version='0.1',
    description="Small test for py_rlock.h",
    author="Neil Schemenauer",
    author_email="nas@arctrix.com",
    license="MIT",
    ext_modules=[
        Extension('rlock_test', ['rlock_test.c']),
    ],
    headers=['py_rlock.h'],
)

setup(**kw)
