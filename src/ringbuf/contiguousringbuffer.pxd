# distutils: language = c++

cdef extern from 'ContiguousBuffer/ContiguousRingbuffer.hpp' nogil:
    cdef cppclass ContiguousRingbuffer [T]:
        ContiguousRingbuffer ()

        bint resize 'Resize' (const size_t size)

        bint poke 'Poke' (T* &dest, size_t& size) except +
        bint write 'Write' (const size_t size) except +

        bint peek 'Peek' (T* &dest, size_t& size) except +
        bint read 'Read' (const size_t size) except +

        size_t size 'Size' () const

        size_t capacity 'Capacity' () const

        void clear 'Clear' ()

        bint is_lock_free 'IsLockFree' () const
