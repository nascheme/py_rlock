#include <Python.h>
#include "py_rlock.h"

static PyMethodDef
rlock_test_functions[] = {
    {NULL, NULL, 0, NULL}
};

static int
rlock_test_exec(PyObject *module)
{
    py_rlock m = {0};
    py_rlock_lock(&m);
    if (!py_rlock_is_locked(&m)) {
        Py_FatalError("mutex is not locked");
    }
    py_rlock_lock(&m);
    if (!py_rlock_is_locked(&m)) {
        Py_FatalError("mutex is not locked");
    }
    py_rlock_unlock(&m);
    py_rlock_unlock(&m);
#if PY_VERSION_HEX > 0x030E00B1
    if (py_rlock_is_locked(&m)) {
        Py_FatalError("mutex is still locked");
    }
#endif
    return 0;
}

static struct 
PyModuleDef_Slot rlock_test_slots[] = {
    {Py_mod_exec, rlock_test_exec},
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
    {0, NULL}
};

static struct PyModuleDef rlock_testmodule = {
    PyModuleDef_HEAD_INIT,
    "rlock_test",
    "Test for py_rlock type.",
    0,
    rlock_test_functions,
    rlock_test_slots,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit_rlock_test(void)
{
    return PyModuleDef_Init(&rlock_testmodule);
}
