"""
Basic test for RWLock (reader-writer lock) implementation.
Tests read/write locking and try_upgrade functionality.
"""

import py_locks


def test_rwlock_read_lock():
    """Test read lock acquisition and release"""
    rwlock = py_locks.RWLock()

    # Test read lock
    rwlock.lock_read()
    rwlock.unlock_read()


def test_rwlock_write_lock():
    """Test write lock acquisition and release"""
    rwlock = py_locks.RWLock()

    # Test write lock
    rwlock.lock_write()
    assert (
        rwlock.is_locked_by_current_thread()
    ), "Write lock should be held by current thread"
    rwlock.unlock_write()
    assert (
        not rwlock.is_locked_by_current_thread()
    ), "Write lock should be released"


def test_rwlock_upgrade_success():
    """Test successful upgrade from read to write lock"""
    rwlock = py_locks.RWLock()

    # Acquire read lock
    rwlock.lock_read()

    # Try to upgrade - should succeed (we're the only reader)
    assert (
        rwlock.try_upgrade()
    ), "Upgrade should succeed when we're the only reader"

    # Should now hold write lock
    assert (
        rwlock.is_locked_by_current_thread()
    ), "Should hold write lock after upgrade"

    # Release write lock
    rwlock.unlock_write()


def test_rwlock_upgrade_recursive_fail():
    """Test that upgrade fails with recursive read locks"""
    rwlock = py_locks.RWLock()

    # Acquire read lock twice (recursive)
    rwlock.lock_read()
    rwlock.lock_read()

    # Try to upgrade - should fail (looks like 2 readers)
    assert (
        not rwlock.try_upgrade()
    ), "Upgrade should fail with recursive read locks"

    # Should still hold read lock
    rwlock.unlock_read()
    rwlock.unlock_read()


def test_rwlock_upgrade_fallback():
    """Test the fallback pattern when upgrade fails"""
    rwlock = py_locks.RWLock()

    # Acquire read lock recursively
    rwlock.lock_read()
    rwlock.lock_read()

    # Try to upgrade
    if rwlock.try_upgrade():
        # Got write lock
        rwlock.unlock_write()
    else:
        # Couldn't upgrade, use fallback pattern
        rwlock.unlock_read()
        rwlock.unlock_read()
        rwlock.lock_write()
        assert (
            rwlock.is_locked_by_current_thread()
        ), "Should hold write lock after fallback"
        rwlock.unlock_write()
