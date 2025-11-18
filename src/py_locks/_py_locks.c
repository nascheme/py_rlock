#include <Python.h>
#include "py_rwlock.h"
#include "py_rlock.h"

// Python object wrapping py_rwlock
typedef struct {
    PyObject_HEAD
    py_rwlock rwlock;
} RWLockObject;

static PyObject *
RWLockObject_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    RWLockObject *self;
    self = (RWLockObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        // Zero-initialize the rwlock
        memset(&self->rwlock, 0, sizeof(py_rwlock));
    }
    return (PyObject *)self;
}

static PyObject *
RWLockObject_lock_read(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rwlock_lock_read(&self->rwlock);
    Py_RETURN_NONE;
}

static PyObject *
RWLockObject_unlock_read(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rwlock_unlock_read(&self->rwlock);
    Py_RETURN_NONE;
}

static PyObject *
RWLockObject_lock_write(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rwlock_lock_write(&self->rwlock);
    Py_RETURN_NONE;
}

static PyObject *
RWLockObject_unlock_write(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rwlock_unlock_write(&self->rwlock);
    Py_RETURN_NONE;
}

static PyObject *
RWLockObject_try_upgrade(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    bool upgraded = py_rwlock_try_upgrade(&self->rwlock);
    return PyBool_FromLong(upgraded);
}

static PyObject *
RWLockObject_is_locked_by_current_thread(RWLockObject *self, PyObject *Py_UNUSED(ignored))
{
    bool is_locked = py_rwlock_is_locked_by_current_thread(&self->rwlock);
    return PyBool_FromLong(is_locked);
}

static PyMethodDef RWLockObject_methods[] = {
    {"lock_read", (PyCFunction)RWLockObject_lock_read, METH_NOARGS,
     "Acquire read lock"},
    {"unlock_read", (PyCFunction)RWLockObject_unlock_read, METH_NOARGS,
     "Release read lock"},
    {"lock_write", (PyCFunction)RWLockObject_lock_write, METH_NOARGS,
     "Acquire write lock"},
    {"unlock_write", (PyCFunction)RWLockObject_unlock_write, METH_NOARGS,
     "Release write lock"},
    {"try_upgrade", (PyCFunction)RWLockObject_try_upgrade, METH_NOARGS,
     "Try to upgrade from read lock to write lock"},
    {"is_locked_by_current_thread", (PyCFunction)RWLockObject_is_locked_by_current_thread, METH_NOARGS,
     "Check if write lock is held by current thread"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject RWLockObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_py_locks.RWLock",
    .tp_doc = "Reader-writer lock",
    .tp_basicsize = sizeof(RWLockObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = RWLockObject_new,
    .tp_methods = RWLockObject_methods,
};

// Python object wrapping py_rlock
typedef struct {
    PyObject_HEAD
    py_rlock rlock;
} RLockObject;

static PyObject *
RLockObject_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    RLockObject *self;
    self = (RLockObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
        // Zero-initialize the rlock
        memset(&self->rlock, 0, sizeof(py_rlock));
    }
    return (PyObject *)self;
}

static PyObject *
RLockObject_lock(RLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rlock_lock(&self->rlock);
    Py_RETURN_NONE;
}

static PyObject *
RLockObject_unlock(RLockObject *self, PyObject *Py_UNUSED(ignored))
{
    py_rlock_unlock(&self->rlock);
    Py_RETURN_NONE;
}

static PyObject *
RLockObject_is_locked_by_current_thread(RLockObject *self, PyObject *Py_UNUSED(ignored))
{
    bool is_locked = py_rlock_is_locked_by_current_thread(&self->rlock);
    return PyBool_FromLong(is_locked);
}

static PyMethodDef RLockObject_methods[] = {
    {"lock", (PyCFunction)RLockObject_lock, METH_NOARGS,
     "Acquire recursive lock"},
    {"unlock", (PyCFunction)RLockObject_unlock, METH_NOARGS,
     "Release recursive lock"},
    {"is_locked_by_current_thread", (PyCFunction)RLockObject_is_locked_by_current_thread, METH_NOARGS,
     "Check if lock is held by current thread"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject RLockObjectType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_py_locks.RLock",
    .tp_doc = "Recursive lock",
    .tp_basicsize = sizeof(RLockObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = RLockObject_new,
    .tp_methods = RLockObject_methods,
};

static PyMethodDef py_locks_methods[] = {
    {NULL, NULL, 0, NULL}
};

static int
py_locks_exec(PyObject *module)
{
    Py_INCREF(&RWLockObjectType);
    if (PyModule_AddObject(module, "RWLock", (PyObject *)&RWLockObjectType) < 0) {
        Py_DECREF(&RWLockObjectType);
        return -1;
    }

    Py_INCREF(&RLockObjectType);
    if (PyModule_AddObject(module, "RLock", (PyObject *)&RLockObjectType) < 0) {
        Py_DECREF(&RLockObjectType);
        return -1;
    }

    return 0;
}

static struct PyModuleDef_Slot py_locks_slots[] = {
    {Py_mod_exec, py_locks_exec},
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
    {0, NULL}
};

static struct PyModuleDef py_locks_module = {
    PyModuleDef_HEAD_INIT,
    "_py_locks",
    "Python wrappers for py_rlock and py_rwlock",
    0,
    py_locks_methods,
    py_locks_slots,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit__py_locks(void)
{
    if (PyType_Ready(&RWLockObjectType) < 0) {
        return NULL;
    }

    if (PyType_Ready(&RLockObjectType) < 0) {
        return NULL;
    }

    return PyModuleDef_Init(&py_locks_module);
}
