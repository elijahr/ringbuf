import struct
from contextlib import contextmanager
from functools import reduce
from operator import mul
from typing import Union, Tuple, Any

from libc.string cimport memcpy
from libc.stdlib cimport malloc, free
from cpython.buffer cimport PyObject_GetBuffer, PyBuffer_Release, PyBUF_ANY_CONTIGUOUS, PyBUF_SIMPLE
from cython.view cimport array as _Array, memoryview as _MemoryView
from cython.parallel cimport prange

Array = _Array
MemoryView = _MemoryView

__all__ = ["RingBuffer", "Array", "MemoryView", "concatenate", ]

cdef class RingBuffer:
    def __cinit__(self, format: str, capacity: int, *args, **kwargs):
        if capacity <= 0:
            raise ValueError('capacity must be > 0')
        self.format = format
        self.capacity = capacity
        self.itemsize = struct.calcsize(format)
        self.queue = new spsc_queue[char](capacity * self.itemsize)

    def __init__(self, format: str, capacity: int, *args, **kwargs):
        ...

    def __dealloc__(self):
        del self.queue

    def pop(self, count: int) -> Union[None, MemoryView]:
        """Pops a maximum of count element from the RingBuffer.

        Returns either whatever data, up to count elements, could be
        popped, or None.
        """
        cdef:
            size_t popped_bytes
            size_t popped_count
            ssize_t size = count * self.itemsize
            _Array arr

        arr = _Array(
            format=self.format,
            shape=(count, ),
            mode='c',
            itemsize=self.itemsize,
            allocate_buffer=True)

        with nogil:
            popped_bytes = self.queue.pop(arr.data, size)

        if popped_bytes > 0:
            return arr[:int(popped_bytes / self.itemsize)]
        else:
            del arr
            return None

    def push(self, data: Any) -> Any:
        """Pushes as many objects from data as possible, returns any remaining
        data.

        :param data: any object which implements the Python buffer protocol.
            This includes, but is not limited to array.array, numpy.ndarray, bytes, bytearray, memoryview,
            cython arrays, and cython typed memoryviews.
        :return: either a slice of the original data for any remaining data which was not pushed to the buffer,
                 or None if all data was pushed.
        """
        cdef:
            Py_buffer py_buffer
            size_t pushed
            object memview = memoryview(data)

        try:
            if memview.ndim != 1:
                raise ValueError('Only 1-dimensional data can be pushed to a RingBuffer')

            elif memview.format != self.format:
                raise TypeError('Mismatched format in input (got %r, expected %r)' % (
                    memview.format, self.format))

            PyObject_GetBuffer(memview, & py_buffer, PyBUF_SIMPLE | PyBUF_ANY_CONTIGUOUS)
            try:
                with nogil:
                    pushed = self.queue.push(< char*>py_buffer.buf, py_buffer.len)
                if pushed != py_buffer.len:
                    return data[pushed / py_buffer.itemsize:]
            finally:
                PyBuffer_Release(& py_buffer)
        finally:
            memview.release()

    @property
    def read_available(self) -> int:
        """Get number of elements that are available for read."""
        return int(self.queue.read_available() / self.itemsize)

    @property
    def write_available(self) -> int:
        """Get the space available for writing."""
        return int(self.queue.write_available() / self.itemsize)

    @property
    def is_lock_free(self) -> bool:
        return self.queue.is_lock_free()

    def reset(self) -> None:
        self.queue.reset()

    cdef void * queue_void_ptr(self):
        return spsc_queue_char_ptr_to_void_ptr(self.queue)


cdef void _test_callback_call(_test_callback_t * callback, void * queue_):
    callback(queue_)


cdef void _test_callback_push(void * queue_):
    cdef:
        # The underlying queue always holds chars
        spsc_queue[char] * queue = void_ptr_to_spsc_queue_char_ptr(queue_)
        double[5] indata = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Cast to char* and multiply # elements with size of double
    queue.push(< char*>indata, sizeof(double) * 5)


def _test_callback_void_ptr():
    """Test for casting spsc_queue from / to void pointer."""
    import array

    buffer = RingBuffer('d', capacity=100)
    _test_callback_call(_test_callback_push, buffer.queue_void_ptr())
    assert bytes(buffer.pop(5)) == bytes(array.array('d', [1.0, 2.0, 3.0, 4.0, 5.0]))


def concatenate(*items: Any) -> Array:
    cdef:
        Py_buffer * py_buffers
        size_t total
        _Array arr
        object item
        object memview
        list memviews = []
        size_t offset = 0
        int i
        vector[copy_instr_t] copy_instrs

    if not items:
        raise ValueError('concatenate requires at least one positional argument')

    py_buffers = <Py_buffer * >malloc(sizeof(Py_buffer) * len(items))

    total = sum(len(a) for a in items)

    try:
        for i, item in enumerate(items):
            memview = memoryview(item)
            PyObject_GetBuffer(memview, & py_buffers[i], PyBUF_SIMPLE | PyBUF_ANY_CONTIGUOUS)
            memviews.append(memview)

            if memview.ndim != 1:
                raise ValueError('Only 1-dimensional data can be joined with concatenate')

            elif i == 0:
                arr = _Array(
                    format=memview.format,
                    shape=(total, ),
                    mode='c',
                    itemsize=memview.itemsize,
                    allocate_buffer=True)

            elif memview.format != arr.format.decode('ascii'):
                raise TypeError('Mismatched format in input (got %r, expected %r)' % (
                    memview.format, arr.format.decode('ascii')))

            copy_instrs.push_back(
                copy_instr_t(
                    addr_and_size_t(arr.data, offset),
                    addr_and_size_t(< char*>py_buffers[i].buf, py_buffers[i].len)))
            offset += py_buffers[i].len

        # copy in parallel
        for i in prange(copy_instrs.size(), nogil=True):
            copy_from_instr(copy_instrs[i])

    finally:
        for i, memview in enumerate(memviews):
            PyBuffer_Release(& py_buffers[i])
            memview.release()
        free(py_buffers)

    return arr


cdef void copy_from_instr(copy_instr_t copy_instr) nogil:
    cdef:
        char * dest = copy_instr.first.first
        size_t offset = copy_instr.first.second
        char * source = copy_instr.second.first
        size_t nbytes = copy_instr.second.second
    memcpy(& dest[offset], source, nbytes)
