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

// Reader-writer lock for use from C extensions, built on PyMutex
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
    unsigned long thread_id = PyThread_get_thread_ident();

    // Handle recursive read from write lock holder
    if (rwlock->level > 0) {
        unsigned long writer_id = ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed);
        assert(writer_id == 0 || writer_id == thread_id);
        rwlock->level--;
        return;
    }

    PyMutex_Lock(&rwlock->reader_lock);
    rwlock->nreaders--;
    if (rwlock->nreaders == 0) {
        // Last reader releases writer lock
        ATOMIC_STORE(&rwlock->writer_id, 0, memory_order_release);
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

    // Check for read-to-write lock upgrade
    PyMutex_Lock(&rwlock->reader_lock);
    if (rwlock->nreaders == 1 && ATOMIC_LOAD(&rwlock->writer_id, memory_order_acquire) == 0) {
        // We're the only reader, upgrade to write lock
        rwlock->level++;
        rwlock->nreaders = 0;
        ATOMIC_STORE(&rwlock->writer_id, thread_id, memory_order_release);
        PyMutex_Unlock(&rwlock->reader_lock);
        return;
    }
    PyMutex_Unlock(&rwlock->reader_lock);

    // Acquire write lock normally
    PyMutex_Lock(&rwlock->writer_lock);
    ATOMIC_STORE(&rwlock->writer_id, thread_id, memory_order_release);
}

void py_rwlock_unlock_write(py_rwlock *rwlock)
{
    unsigned long thread_id = PyThread_get_thread_ident();
    assert(ATOMIC_LOAD(&rwlock->writer_id, memory_order_relaxed) == thread_id);

    // Handle recursive write lock
    if (rwlock->level > 0) {
        rwlock->level--;
        return;
    }

    // Use release: synchronize all writes before releasing the lock
    ATOMIC_STORE(&rwlock->writer_id, 0, memory_order_release);
    PyMutex_Unlock(&rwlock->writer_lock);
}
