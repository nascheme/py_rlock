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


If you are using C++, you can use standard C++ library features, like
`std::shared_mutex`.  With standard library locking primitives you must detach
from the interpreter (e.g. release the GIL in the GIL-enabled build) before a
possibly blocking call to acquire the mutex. Otherwise you might cause a
deadlock either with the GIL or with e.g. the garbage collector on the
free-threaded build.  PyMutex has built-in deadlock protection for the
interpreter and can't deadlock in that way.
