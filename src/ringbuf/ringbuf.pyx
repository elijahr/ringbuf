import struct
from contextlib import contextmanager
from functools import reduce
from operator import mul
from typing import Union, Tuple, Any

from libc.string cimport memcpy
from cython.view cimport array as _Array, memoryview as _MemoryView

from .exceptions import Overflow, Underflow

__all__ = ['RingBuffer', 'Array', 'MemoryView']


MemoryView = _MemoryView
MemoryViewSlice = None


class Array(_Array):

    def __setitem__(self, item, value: Any):
        cdef object view = memoryview(value)
        try:
            if view.format != self._format:
                raise TypeError('Mismatched format (got %r, expected %r)' % (format, self._format))
            self.memview[item] = value
        finally:
            del view

    @property
    def _format(self):
        return (<_Array>self).format.decode('ascii')


cdef class RingBuffer:
    def __cinit__(self, format: str, capacity: int):
        self.format = format
        self.itemsize = struct.calcsize(format)
        self.buf = new ContiguousRingbuffer[char]()
        self.resize(capacity * self.itemsize)

    def __init__(self, format: str, capacity: int):
        ...

    def __dealloc__(self):
        del self.buf

    cpdef void resize(RingBuffer self, const size_t size):
        cdef:
            bint resized
        with nogil:
            resized = self.buf.resize(size)
        if not resized:
            raise Overflow

    @contextmanager
    def poke(RingBuffer self, shape: Union[int, Tuple[int, ...]]) -> Array:
        cdef:
            long bytesize
            size_t bs
            bint poked
            char* data = NULL
            object arr

        if not isinstance(shape, tuple):
            shape = (shape, )

        bytesize = reduce(mul, shape, self.itemsize)

        if bytesize <= 0:
            raise ValueError('Invalid shape %s' % repr(shape))

        bs = <size_t>bytesize

        with nogil:
            poked = self.buf.poke(data, bs)

        if not poked:
            raise Overflow

        arr = Array(
            format=self.format,
            shape=shape,
            mode='c',
            itemsize=self.itemsize,
            allocate_buffer=False)
        (<_Array>arr).data = data

        try:
            yield arr
            self.buf.write(bytesize)
        finally:
            del arr

    def peek(RingBuffer self, shape: Union[int, Tuple[int, ...]]) -> Array:
        return self.read(shape, peek=True)

    def read(RingBuffer self, shape: Union[int, Tuple[int, ...]], peek: bool = False) -> Array:
        cdef:
            long bytesize
            size_t bs
            bint peeked_all
            char* data = NULL
            object arr
            bint read

        if not isinstance(shape, tuple):
            shape = (shape, )

        bytesize = reduce(mul, shape, self.itemsize)

        if bytesize <= 0:
            raise ValueError('Invalid shape %s' % repr(shape))

        bs = <size_t>bytesize

        with nogil:
            peeked = self.buf.peek(data, bs)

        if not peeked:
            raise Underflow

        arr = Array(
            format=self.format,
            shape=shape,
            mode='c',
            itemsize=self.itemsize,
            allocate_buffer=True)

        with nogil:
            memcpy((<_Array>arr).data, data, bytesize)

        if not peek:
            with nogil:
                read = self.buf.read(bytesize)
            if not read:
                raise Underflow

        return arr

    cpdef void clear(RingBuffer self):
        with nogil:
            self.buf.clear()

    @property
    def size(RingBuffer self) -> int:
        cdef:
            size_t size
        with nogil:
            size = self.buf.size()
        return int(size / self.itemsize)

    @property
    def capacity(RingBuffer self) -> int:
        cdef:
            size_t capacity
        with nogil:
            capacity = self.buf.capacity()
        return int(capacity / self.itemsize)

    @property
    def is_lock_free(RingBuffer self) -> bool:
        cdef:
            bint is_lock_free
        with nogil:
            is_lock_free = self.buf.is_lock_free()
        return is_lock_free
