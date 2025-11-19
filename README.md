# py_rlock

## Overview

This package provides two header files intended for use by Python extensions
written in pure C:

- **`py_rlock.h`** - Recursive lock
- **`py_rwlock.h`** - Reader-writer lock

The underlying mutex used by these locks is the PyMutex that is built-in to Python.
This means you do not need to detach from the Python thread-state when
acquiring these locks.

You can either copy the code from py_rlock.h and py_rwlock.h or copy the whole
files into your project. Your C compiler needs to support C11 atomics. For
MSVC, likely you will need to set the `/experimental:c11atomics` flag.  See
the `setup.py` file for an example of how to set that flag.

If you are using C++, you do not need this code and can use standard C++
library features, like std::shared_mutex. With standard library locking
primitives you must detach from the interpreter (e.g. release the GIL in the
GIL-enabled build) before a possibly blocking call to acquire a standard
library lock. Otherwise you might cause a deadlock either with the GIL or with
e.g. the garbage collector on the free-threaded build. PyMutex has built-in
deadlock protection for the interpreter and can't deadlock in that way.

Example usage for a reentrant lock:
```
#include "py_rlock.h"
...
py_rlock lock = {0};
...
py_rlock_lock(&lock);
// reading or writing of shared state
py_rlock_unlock(&lock);
```

Example usage for a reader-writer lock:
```
#include "py_rwlock.h"
...
py_rwlock lock = {0};
...
py_rwlock_lock_read(&lock);
// reading of shared state
py_rwlock_unlock_read(&lock);
...
py_rwlock_lock_write(&lock);
// writing of shared state
py_rwlock_unlock_write(&lock);
```

## Symbols from py_rlock.h

### Structure: `py_rlock`

A recursive lock that allows the same thread to acquire the lock multiple
times. Must be zero-initialized before use (e.g., `py_rlock lock = {0};` or
with `calloc`).

### Functions

#### `void py_rlock_lock(py_rlock *m)`

Acquires the recursive lock. If the calling thread already holds the lock,
increments the recursion level. Otherwise, blocks until the lock becomes
available.

**Pre-conditions:**
- Lock must be zero-initialized
- Safe to call from any thread

**Post-conditions:**
- Calling thread owns the lock
- Recursion level incremented if already owned by caller

#### `void py_rlock_unlock(py_rlock *m)`

Releases one level of the recursive lock. If the recursion level is greater
than zero, decrements it. Otherwise, releases the lock entirely.

**Pre-conditions:**
- Calling thread must currently hold the lock (assertion failure otherwise)

**Post-conditions:**
- If recursion level > 0: level decremented, lock still held
- If recursion level == 0: lock released, available for other threads

#### `bool py_rlock_is_locked_by_current_thread(py_rlock *m)`

Checks whether the calling thread currently holds the lock.

**Returns:** `true` if calling thread owns the lock, `false` otherwise

---

## Symbols from py_rwlock.h

### Structure: `py_rwlock`

A reader-writer lock allowing multiple concurrent readers or one exclusive
writer. Based on a two-mutex design. Must be zero-initialized before use.

**Concurrency model:**
- Multiple readers can hold the lock simultaneously
- Writers have exclusive access (no readers or other writers)
- Writers can recursively acquire write locks
- Threads holding write locks can also acquire read locks

### Functions

#### `void py_rwlock_lock_read(py_rwlock *rwlock)`

Acquires a read lock. Multiple threads can hold read locks concurrently. If the
calling thread already holds a write lock, increments the recursion level
instead.

**Pre-conditions:**
- Lock must be zero-initialized
- Safe to call from any thread

**Post-conditions:**
- Calling thread holds a read lock
- Other readers can also acquire the lock
- Writers will block until all readers release

#### `void py_rwlock_unlock_read(py_rwlock *rwlock)`

Releases a read lock. If this was acquired while holding a write lock,
decrements the recursion level instead.

**Pre-conditions:**
- Calling thread must currently hold a read lock

**Post-conditions:**
- Read lock released
- If this was the last reader, waiting writers can proceed

#### `void py_rwlock_lock_write(py_rwlock *rwlock)`

Acquires a write lock, blocking until all readers and other writers have
released. Supports recursive acquisition by the same thread.

**Pre-conditions:**
- Lock must be zero-initialized
- Safe to call from any thread

**Post-conditions:**
- Calling thread has exclusive write access
- All readers and other writers are blocked

#### `void py_rwlock_unlock_write(py_rwlock *rwlock)`

Releases a write lock. If acquired recursively, decrements the recursion level.

**Pre-conditions:**
- Calling thread must currently hold the write lock (assertion failure otherwise)

**Post-conditions:**
- If recursion level > 0: level decremented, write lock still held
- If recursion level == 0: write lock released, readers/writers can proceed

#### `bool py_rwlock_is_locked_by_current_thread(py_rwlock *rwlock)`

Checks whether the calling thread currently holds the write lock.

**Returns:** `true` if calling thread holds the write lock, `false` otherwise

**Note:** Does not indicate read lock ownership, only write locks.

#### `bool py_rwlock_try_upgrade(py_rwlock *rwlock)`

Attempts to atomically upgrade from a read lock to a write lock. This is useful
for read-modify-write patterns where you want to avoid releasing the lock
between reading and writing.

**Pre-conditions:**
- Calling thread must hold exactly one read lock (non-recursive)
- Thread must not already hold the write lock

**Post-conditions (on success - returns `true`):**
- Read lock is released
- Write lock is acquired
- Transition is atomic (no other thread can intervene)

**Post-conditions (on failure - returns `false`):**
- Original read lock is still held
- No state change occurred

**Upgrade fails when:**
- Other readers are present
- Calling thread has recursively acquired read locks

**Typical usage pattern:**
```c
py_rwlock_lock_read(&lock);
// Read shared state
int value = read_data();

if (needs_update(value)) {
    if (py_rwlock_try_upgrade(&lock)) {
        // Success! We now have exclusive write access
        // State hasn't changed since we read it
        write_data(updated_value);
        py_rwlock_unlock_write(&lock);
    } else {
        // Failed - other readers present
        // Must release and reacquire
        py_rwlock_unlock_read(&lock);
        py_rwlock_lock_write(&lock);
        // Must re-read state since we released the lock
        value = read_data();
        if (needs_update(value)) {
            write_data(updated_value);
        }
        py_rwlock_unlock_write(&lock);
    }
} else {
    py_rwlock_unlock_read(&lock);
}
```

---

## Usage

These two header files are quite small and are intended to be copied
(vendored) into the source tree of your project.  If you are compiling on
a Windows computer with MSVC, you will need to enable atomics, using the
`/experimental:c11atomics` build flag.  Other compilers like GCC and Clang
should already include the required C11 atomics.


## Python Module

The `py_locks` Python module is purely for testing the implementation of these
locks. It provides Python types that wrap the C functions and allow the locks
to be exercised from pure Python code.


### Installation (for testing)

```bash
# setup venv and build extension
uv sync --python=3.14t
uv run python setup.py build_ext --inplace
source .venv/bin/activate
```

## Running tests

The repository includes comprehensive tests using pytest:

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_rlock.py
pytest tests/test_rwlock.py

# Run stress tests via pytest
pytest tests/test_rlock_stress.py
pytest tests/test_rwlock_stress.py
```

### Standalone Stress Tests

Multi-threaded stress tests can also be run directly for debugging and
performance analysis:

```bash
# Run RLock stress test
python -m py_locks.stress_rlock --threads 16 --duration 10

# Run RWLock stress test
python -m py_locks.stress_rwlock --threads 16 --duration 10

# Run RWLock stress test, with upgrade function
python -m py_locks.stress_rwlock --threads 4 --duration 10 -u

# View help for options
python -m py_locks.stress_rlock --help
```

## License

See LICENSE.md (MIT).
