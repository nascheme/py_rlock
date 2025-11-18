"""
Python wrappers for py_rlock and py_rwlock.

This module provides Python bindings for C-based locking primitives:
- RLock: Recursive lock (reentrant mutex)
- RWLock: Reader-writer lock

These locks are built on PyMutex and designed for use in free-threaded Python.
"""

from ._py_locks import RLock, RWLock

__version__ = "0.1.0"
__all__ = ["RLock", "RWLock"]
