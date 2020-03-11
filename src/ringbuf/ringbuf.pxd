# distutils: language = c++

from .contiguousringbuffer cimport ContiguousRingbuffer


cdef class RingBuffer:
    cdef:
        ContiguousRingbuffer[char] *buf

        # The data's format character, specifying the type and bytesize of samples
        # see https://docs.python.org/3/library/struct.html#format-characters
        readonly str format

        # The number of bytes per sample, as determined by format
        readonly size_t itemsize

    cpdef void resize(RingBuffer self, const size_t size)

    cpdef void clear(RingBuffer self)
