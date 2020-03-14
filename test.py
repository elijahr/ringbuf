
import numpy as np
import pytest

from ringbuf import RingBuffer, Underflow
from ringbuf.ringbuf import _test_callback_void_ptr
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
        yield np.linspace(start, stop, num=2**16, dtype=np.dtype(format))

    for format, start, stop in (
            ('f', FLT_MIN, FLT_MAX),
            ('d', DBL_MIN, DBL_MAX),
    ):
        yield np.linspace(start, stop, num=2**16, dtype=np.dtype(format))


@pytest.fixture(params=tuple(_expected()), ids=lambda e: '%s-%r' % (e.dtype.char, e.shape))
def expected(request):
    return request.param


def test_push_pop(expected):
    capacity = expected.size

    buffer = RingBuffer(format=expected.dtype.char, capacity=capacity)
    assert buffer.is_lock_free

    assert buffer.read_available == 0
    assert buffer.write_available == capacity

    # test full write
    remaining = buffer.push(expected)
    assert remaining is None
    assert buffer.read_available == capacity
    assert buffer.write_available == 0

    # test full read
    assert np.array_equal(
        buffer.pop(capacity),
        expected)
    assert buffer.read_available == 0
    assert buffer.write_available == capacity

    # test writing chunks
    prev_read_available = 0
    for chunk in np.array_split(expected, 6):
        remaining = buffer.push(chunk)
        assert remaining is None
        assert buffer.read_available == prev_read_available + len(chunk)
        prev_read_available += len(chunk)

    assert buffer.read_available == capacity
    assert buffer.write_available == 0

    # test reading chunks
    prev_write_available = 0
    for chunk in np.array_split(expected, 6):
        assert np.array_equal(
            buffer.pop(len(chunk)),
            chunk)
        assert buffer.write_available == prev_write_available + len(chunk)
        prev_write_available += len(chunk)

    # test reading more than available
    buffer.push(expected[:10])
    assert np.array_equal(
        buffer.pop(capacity),
        expected[:10])

    # teest reading more than capacity
    buffer.push(expected)
    assert np.array_equal(
        buffer.pop(capacity + 123),
        expected)


def test_underflow():
    buffer = RingBuffer(format='b', capacity=1)
    with pytest.raises(Underflow):
        buffer.pop(1)


def test_overflow():
    buffer = RingBuffer(format='B', capacity=7)
    remaining = buffer.push(b'spam')
    assert remaining is None
    remaining = buffer.push(b'eggs')
    assert bytes(remaining) == b's'
    assert bytes(buffer.pop(buffer.capacity)) == b'spamegg'


def test_invalid():
    with pytest.raises(ValueError):
        RingBuffer(format='B', capacity=0)

    buffer = RingBuffer(format='B', capacity=10)

    # Empty data is okay
    buffer.push(b'')

    buffer.push(b'hello')

    # Can't pop negative or zero
    for i in (-1, 0):
        with pytest.raises(ValueError):
            buffer.pop(i)

    # Types must match
    with pytest.raises(TypeError):
        buffer.push(np.array('f', [1.0]))


def test_callback_void_ptr():
    _test_callback_void_ptr()