"""
Pytest wrapper for RWLock stress test.
Imports and runs the stress test from the py_locks package.
"""

from py_locks.stress_rwlock import run_stress_test, run_upgrade_test


def test_rwlock_stress_default():
    """Run RWLock stress test with default parameters"""
    success = run_stress_test(threads=8, duration=4)
    assert success, "RWLock stress test failed"


def test_rwlock_upgrade():
    """Run RWLock upgrade test with low contention"""
    success = run_upgrade_test(threads=4, duration=4)
    assert success, "RWLock upgrade test failed"
