# distutils: language = c++

cimport libcpp


cdef extern from '<boost/lockfree/spsc_queue.hpp>' namespace 'boost::lockfree' nogil:
    cdef cppclass spsc_queue[T]:
        spsc_queue(size_t size)

        # # Pops one object from ringbuffer.
        # libcpp.bool pop(T & t)
        #
        # # Pops one object from ringbuffer.
        # size_t pop[T](T & ret)

        # Pops a maximum of size objects from ringbuffer.
        size_t pop(T * ret, size_t size)

        # Pushes as many objects from the array t as there is space.
        size_t push(const T * t, size_t size)

        # Pushes as many objects from the array t as there is space available.
        size_t push[T](const T & t)

        # get number of elements that are available for read
        size_t read_available() const

        # get write space to write elements
        size_t write_available() const

        libcpp.bool is_lock_free()


cdef extern from *:
    spsc_queue[char]* void_ptr_to_spsc_queue_char_ptr 'static_cast<boost::lockfree::spsc_queue<char>*>' (void*) nogil except NULL
    void* spsc_queue_char_ptr_to_void_ptr 'static_cast<void*>' (spsc_queue[char]*) nogil except NULL