// Based on rwlock.pxi from LXML, written by
// Kumar Aditya <kumaraditya@python.org>
// Converted to pure C with the assistance of Claude Sonnet 4.5

#if ((__STDC_VERSION__ >= 201112L) && !defined(__STDC_NO_ATOMICS__))
#include <stdatomic.h>
#include <stdbool.h>
#define ATOMIC_LOAD(addr, order) atomic_load_explicit(addr, order)
#define ATOMIC_STORE(addr, val, order) atomic_store_explicit(addr, val, order)
#define ATOMIC_T(T) _Atomic(T)
#else
// for MSVC, might need to enable the /experimental:c11atomics build flag
#error "Require compiler support for C11 atomics."
#endif

// Reader-writer lock for use from C extensions, built using PyMutex
// Based on the two-mutex design from lxml's rwlock.pxi
//
// Usage: Zero-initialize the struct (e.g., = {0} or calloc).
// No explicit init or destroy functions are needed.
typedef struct {
    PyMutex reader_lock;        // Protects reader count
    PyMutex writer_lock;        // Ensures exclusive write access
    int32_t nreaders;           // Number of active readers (protected by reader_lock)
    ATOMIC_T(unsigned long) writer_id;  // Thread ID of current writer (0 = locked by readers)
    unsigned long level;        // Recursion level for write locks
} py_rwlock;

////////////////////////////////////////////////////////////////////

void py_rwlock_lock_read(py_rwlock *rwlock)
{
    unsigned long thread_id = PyThread_get_thread_ident();

    // If current thread holds the write lock, allow recursive read
    if (ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed) == thread_id) {
        rwlock->level++;
        return;
    }

    PyMutex_Lock(&rwlock->reader_lock);
    rwlock->nreaders++;
    if (rwlock->nreaders == 1) {
        // First reader acquires writer lock to block writers
        PyMutex_Lock(&rwlock->writer_lock);
        // Zero means locked by readers
        ATOMIC_STORE(&rwlock->writer_id, 0, memory_order_release);
    }
    PyMutex_Unlock(&rwlock->reader_lock);
}

void py_rwlock_unlock_read(py_rwlock *rwlock)
{
    // Handle recursive read from write lock holder
    if (rwlock->level > 0) {
        #ifndef NDEBUG
        unsigned long thread_id = PyThread_get_thread_ident();
        unsigned long writer_id = ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed);
        assert(writer_id == 0 || writer_id == thread_id);
        #endif
        rwlock->level--;
        return;
    }

    PyMutex_Lock(&rwlock->reader_lock);
    rwlock->nreaders--;
    if (rwlock->nreaders == 0) {
        // Last reader releases writer lock
        PyMutex_Unlock(&rwlock->writer_lock);
    }
    PyMutex_Unlock(&rwlock->reader_lock);
}

void py_rwlock_lock_write(py_rwlock *rwlock)
{
    unsigned long thread_id = PyThread_get_thread_ident();

    // Handle recursive write lock
    if (ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed) == thread_id) {
        rwlock->level++;
        return;
    }

    // Acquire write lock
    PyMutex_Lock(&rwlock->writer_lock);
    ATOMIC_STORE(&rwlock->writer_id, thread_id, memory_order_release);
}

void py_rwlock_unlock_write(py_rwlock *rwlock)
{
    #ifndef NDEBUG
    unsigned long thread_id = PyThread_get_thread_ident();
    assert(ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed) == thread_id);
    #endif

    // Handle recursive write lock
    if (rwlock->level > 0) {
        rwlock->level--;
        return;
    }

    // Use release: synchronize all writes before releasing the lock
    ATOMIC_STORE(&rwlock->writer_id, 0, memory_order_release);
    PyMutex_Unlock(&rwlock->writer_lock);
}

bool py_rwlock_is_locked_by_current_thread(py_rwlock *rwlock)
{
    unsigned long thread = PyThread_get_thread_ident();
    return ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed) == thread;
}

// Try to upgrade from read lock to write lock
// Returns true if upgrade succeeded, false otherwise
//
// Assumes caller currently holds exactly one read lock (non-recursive).
// If successful, caller now holds write lock (read lock is released).
// If unsuccessful, caller still holds the original read lock.
//
// Upgrade fails if:
// - Other readers are present, OR
// - Caller holds read lock recursively (appears as multiple readers)
bool py_rwlock_try_upgrade(py_rwlock *rwlock)
{
    unsigned long thread_id = PyThread_get_thread_ident();

    PyMutex_Lock(&rwlock->reader_lock);

    // Check if we're the only reader
    if (rwlock->nreaders == 1) {
        // We're the only reader, can upgrade
        rwlock->nreaders = 0;

        // Acquire write lock (we still hold writer_lock from being a reader)
        ATOMIC_STORE(&rwlock->writer_id, thread_id, memory_order_release);

        PyMutex_Unlock(&rwlock->reader_lock);
        return true;
    }

    // Cannot upgrade - other readers present (or we have recursive read locks)
    PyMutex_Unlock(&rwlock->reader_lock);
    return false;
}

