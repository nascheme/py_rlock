"""
Main entry point when running py_locks as a module.
Provides information about available stress tests.
"""

import sys

help_text = """
py_locks: Python locking primitives (RLock and RWLock)

To run stress tests:
  python -m py_locks.stress_rlock  [-t THREADS] [-d DURATION]
  python -m py_locks.stress_rwlock [-t THREADS] [-d DURATION]

Options:
  -t, --threads   Number of worker threads (default: 8)
  -d, --duration  Test duration in seconds (default: 10)

Examples:
  python -m py_locks.stress_rlock -t 16 -d 30
  python -m py_locks.stress_rwlock -t 8 -d 10
"""

if __name__ == "__main__":
    print(help_text)
    sys.exit(0)
