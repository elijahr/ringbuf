
import numpy as np
import pytest

from ringbuf import RingBuffer, Overflow, Underflow
from ringbuf.libc_constants import SCHAR_MIN, SCHAR_MAX, UCHAR_MAX, SHRT_MIN, SHRT_MAX, USHRT_MAX, INT_MIN, \
    INT_MAX, UINT_MAX, LONG_MIN, LONG_MAX, ULONG_MAX, LLONG_MIN, LLONG_MAX, ULLONG_MAX, FLT_MIN, FLT_MAX, DBL_MIN, \
    DBL_MAX


def _expected():
    for format, start, stop in (
            ('b', SCHAR_MIN, SCHAR_MAX),
            ('B', 0, UCHAR_MAX),
            ('h', SHRT_MIN, SHRT_MAX),
            ('H', 0, USHRT_MAX),
            ('i', INT_MIN, INT_MAX),
            ('I', 0, UINT_MAX),
            ('l', LONG_MIN, LONG_MAX),
            ('L', 0, ULONG_MAX),
            ('q', LLONG_MIN, LLONG_MAX),
            ('Q', 0, ULLONG_MAX),
    ):
        arr = np.linspace(start, stop, num=2**16, dtype=np.dtype(format))
        yield arr
        yield arr.reshape((int(len(arr) / 2), 2))

    for format, start, stop in (
            ('f', FLT_MIN, FLT_MAX),
            ('d', DBL_MIN, DBL_MAX),
    ):
        arr = np.linspace(start, stop, num=2**16, dtype=np.dtype(format))
        yield arr
        yield arr.reshape((int(len(arr) / 2), 2))


@pytest.fixture(params=tuple(_expected()), ids=lambda e: '%s-%r' % (e.dtype.char, e.shape))
def expected(request):
    return request.param


def test_buffer(expected):
    capacity = expected.size

    buffer = RingBuffer(format=expected.dtype.char, capacity=capacity)

    assert buffer.size == 0
    assert buffer.capacity == capacity

    # peek/poke 0 raises a ValueError
    for shape in (0, (0,)):
        with pytest.raises(ValueError):
            buffer.peek(shape)
        with pytest.raises(ValueError):
            with buffer.poke(shape):
                ...

    # peek 1 raises underflow
    for shape in (1, (1, )):
        with pytest.raises(Underflow):
            buffer.peek(shape)

    with buffer.poke(expected.shape) as data:
        assert data.shape == expected.shape
        data[:] = expected

    assert np.array_equal(buffer.peek(expected.shape), expected)
    assert buffer.size == buffer.capacity

    # buffer is full
    with pytest.raises(Overflow):
        with buffer.poke((1,)):
            ...

    chunks = np.split(expected, 4)
    data = buffer.read(chunks[0].shape)
    assert buffer.size == buffer.capacity * (3/4)
    assert data.shape == chunks[0].shape
    assert np.array_equal(data, chunks[0])

    data = buffer.read(chunks[1].shape)
    assert buffer.size == buffer.capacity * (1/2)
    assert data.shape == chunks[1].shape
    assert np.array_equal(data, chunks[1])

    data = buffer.read(chunks[2].shape)
    assert buffer.size == buffer.capacity * (1/4)
    assert data.shape == chunks[2].shape
    assert np.array_equal(data, chunks[2])

    with buffer.poke(chunks[0].shape) as data:
        assert data.shape == chunks[0].shape
        data[:] = chunks[0]

    assert buffer.size == buffer.capacity * (1/2)

    data = buffer.read(chunks[3].shape)
    assert buffer.size == buffer.capacity * (1/4)
    assert data.shape == chunks[3].shape
    assert np.array_equal(data, chunks[3])

    data = buffer.read(chunks[0].shape)
    assert buffer.size == 0
    assert data.shape == chunks[0].shape
    assert np.array_equal(data, chunks[0])

    with pytest.raises(Underflow):
        buffer.read(chunks[0].shape)
