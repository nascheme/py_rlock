# py_rlock

This is a relatively small fragment of C code that can be used to implement
a recursive mutex on top of `PyMutex`.  You can either copy the code from
`py_rlock.h` or copy the whole file into your project.  Your C compiler
needs to support C11 atomics.  For MSVC, likely you will need to set the
`/experimental:c11atomics` flag.

Example usage:

    py_rlock lock = {0};
    ...
    py_rlock_lock(&lock);
    ...
    py_rlock_unlock(&lock);
