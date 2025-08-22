
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

// recursive mutex, similar to _PyRecursiveMutex or threading.RLock
typedef struct {
    PyMutex mutex;
    ATOMIC_T(unsigned long) owner;
    size_t level;
} py_rlock;

////////////////////////////////////////////////////////////////////

void py_rlock_lock(py_rlock *m)
{
    unsigned long thread = PyThread_get_thread_ident();
    if (ATOMIC_LOAD(&m->owner, memory_order_relaxed) == thread) {
        m->level++;
        return;
    }
    PyMutex_Lock(&m->mutex);
    ATOMIC_STORE(&m->owner, thread, memory_order_relaxed);
    assert(m->level == 0);
}

void py_rlock_unlock(py_rlock *m)
{
    unsigned long thread = PyThread_get_thread_ident();
    if (ATOMIC_LOAD(&m->owner, memory_order_relaxed) != thread) {
        assert(0);
    }
    if (m->level > 0) {
        m->level--;
        return;
    }
    ATOMIC_STORE(&m->owner, 0, memory_order_relaxed);
    PyMutex_Unlock(&m->mutex);
}

bool py_rlock_is_locked_by_current_thread(py_rlock *m)
{
    unsigned long thread = PyThread_get_thread_ident();
    return ATOMIC_LOAD(&m->owner, memory_order_relaxed) == thread;
}
