#!/usr/bin/env python3

import os
import sys

from setuptools import Extension, setup

# Path to header files (in project root)
root_dir = os.path.dirname(os.path.abspath(__file__))
include_dirs = [root_dir]

msvc_compile_args = [
    # 1. Flag to enable C11 atomics (experimental feature)
    '/experimental:c11atomics',
    # 2. Flag to enable C11 standard (required for atomics)
    # Use /std:c17 for C17 support, or /std:c11 for C11
    '/std:c17',
]

if sys.platform == 'win32':
    extra_args = msvc_compile_args
else:
    extra_args = []

setup(
    ext_modules=[
        Extension(
            'py_locks._py_locks',
            sources=['src/py_locks/_py_locks.c'],
            include_dirs=include_dirs,
            extra_compile_args=extra_args,
        ),
    ],
)
