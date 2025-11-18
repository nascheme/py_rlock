#!/usr/bin/env python3

import os

from setuptools import Extension, setup

# Path to header files (in project root)
root_dir = os.path.dirname(os.path.abspath(__file__))
include_dirs = [root_dir]

setup(
    ext_modules=[
        Extension(
            'py_locks._py_locks',
            sources=['src/py_locks/_py_locks.c'],
            include_dirs=include_dirs,
        ),
    ],
)
