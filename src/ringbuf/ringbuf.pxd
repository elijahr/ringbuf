# distutils: language = c++

from libcpp.pair cimport pair
from libcpp.vector cimport vector

from .boost cimport spsc_queue
from .boost cimport void_ptr_to_spsc_queue_char_ptr, spsc_queue_char_ptr_to_void_ptr


cdef class RingBuffer:
    cdef:
        spsc_queue[char] *queue

        # The data's format character, specifying the type and bytesize of samples
        # see https://docs.python.org/3/library/struct.html#format-characters
        readonly str format

        # The number of samples this buffer can contain
        readonly size_t capacity

        # The number of bytes per sample, as determined by format
        readonly size_t itemsize

    cdef void* queue_void_ptr(self)


# Tests for void ptr casting / callback usage
ctypedef void _test_callback_t(void* queue_)

cdef void _test_callback_call(_test_callback_t* callback, void* queue_)

cdef void _test_callback_push(void* queue_)

ctypedef pair[char*, size_t] addr_and_size_t
ctypedef pair[addr_and_size_t, addr_and_size_t] copy_instr_t


cdef void copy_from_instr(copy_instr_t copy_instr) nogil