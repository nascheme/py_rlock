"""
Pytest wrapper for RLock stress test.
Imports and runs the stress test from the py_locks package.
"""

from py_locks.stress_rlock import run_stress_test


def test_rlock_stress_default():
    """Run RLock stress test with default parameters"""
    success = run_stress_test(threads=8, duration=4)
    assert success, "RLock stress test failed"
