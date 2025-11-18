"""
Basic test for RLock (recursive lock) implementation.
Tests basic locking, recursive locking, and is_locked_by_current_thread().
"""

import py_locks


def test_rlock_acquire_and_detect():
    """Test that lock can be acquired and is detected by current thread"""
    m = py_locks.RLock()
    m.lock()
    assert (
        m.is_locked_by_current_thread()
    ), "Lock should be held by current thread after lock()"
    m.unlock()


def test_rlock_recursive_locking():
    """Test recursive locking functionality"""
    m = py_locks.RLock()

    # Lock it twice
    m.lock()
    m.lock()
    assert (
        m.is_locked_by_current_thread()
    ), "Lock should still be held after recursive lock()"

    # Unlock once - should still be held
    m.unlock()
    assert (
        m.is_locked_by_current_thread()
    ), "Lock should still be held after one unlock()"

    # Unlock again - should be released
    m.unlock()
    assert (
        not m.is_locked_by_current_thread()
    ), "Lock should not be held after final unlock()"


def test_rlock_full_lifecycle():
    """Test full lock lifecycle with recursive locking"""
    m = py_locks.RLock()

    # Initial state - not locked
    assert not m.is_locked_by_current_thread()

    # Lock it
    m.lock()
    assert m.is_locked_by_current_thread()

    # Lock it again (recursive)
    m.lock()
    assert m.is_locked_by_current_thread()

    # Unlock once
    m.unlock()
    assert m.is_locked_by_current_thread()

    # Unlock again
    m.unlock()
    assert not m.is_locked_by_current_thread()
