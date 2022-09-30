#!/usr/bin/env python3

# pylint: disable=no-name-in-module,redefined-outer-name,wrong-import-position

# This file is nested under test/ to ensure ringbuf import comes from
# site-packages, not project directory.

import struct

import numpy as np
import pytest

from ringbuf import (
    Array,
    RingBuffer,
    concatenate,
)
from ringbuf.libc_constants import (
    DBL_MAX,
    DBL_MIN,
    FLT_MAX,
    FLT_MIN,
    INT_MAX,
    INT_MIN,
    LLONG_MAX,
    LLONG_MIN,
    LONG_MAX,
    LONG_MIN,
    SCHAR_MAX,
    SCHAR_MIN,
    SHRT_MAX,
    SHRT_MIN,
    UCHAR_MAX,
    UINT_MAX,
    ULLONG_MAX,
    ULONG_MAX,
    USHRT_MAX,
)
from ringbuf.ringbufcy import (
    _test_callback_void_ptr,
)


def _expected():
    for fmt, start, stop in (
        ("b", SCHAR_MIN, SCHAR_MAX),
        ("B", 0, UCHAR_MAX),
        ("h", SHRT_MIN, SHRT_MAX),
        ("H", 0, USHRT_MAX),
        ("i", INT_MIN, INT_MAX),
        ("I", 0, UINT_MAX),
        ("l", LONG_MIN, LONG_MAX),
        ("L", 0, ULONG_MAX),
        ("q", LLONG_MIN, LLONG_MAX),
        ("Q", 0, ULLONG_MAX),
    ):
        yield np.linspace(start, stop, num=2**16, dtype=np.dtype(fmt))

    for fmt, start, stop in (
        ("f", FLT_MIN, FLT_MAX),
        ("d", DBL_MIN, DBL_MAX),
    ):
        yield np.linspace(start, stop, num=2**16, dtype=np.dtype(fmt))


@pytest.fixture(
    params=tuple(_expected()),
    ids=lambda e: f"{e.dtype.char}-{repr(e.shape)}",
)
def expected(request):
    return request.param


def test_ringbuffer_push_pop(expected):
    capacity = expected.size

    buffer = RingBuffer(format=expected.dtype.char, capacity=capacity)
    assert buffer.capacity == capacity
    assert buffer.is_lock_free

    assert buffer.read_available == 0
    assert buffer.write_available == capacity

    # test full write
    remaining = buffer.push(expected)
    assert remaining is None
    assert buffer.read_available == capacity
    assert buffer.write_available == 0

    # test full read
    assert np.array_equal(buffer.pop(capacity), expected)
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
        assert np.array_equal(buffer.pop(len(chunk)), chunk)
        assert buffer.write_available == prev_write_available + len(chunk)
        prev_write_available += len(chunk)

    # test reading more than available
    buffer.push(expected[:10])
    assert np.array_equal(buffer.pop(capacity), expected[:10])

    # teest reading more than capacity
    buffer.push(expected)
    assert np.array_equal(buffer.pop(capacity + 123), expected)


def test_ringbuffer_underflow():
    buffer = RingBuffer(format="b", capacity=1)
    assert buffer.pop(1) is None


def test_ringbuffer_overflow():
    buffer = RingBuffer(format="B", capacity=7)
    remaining = buffer.push(b"spam")
    assert remaining is None
    remaining = buffer.push(b"eggs")
    assert bytes(remaining) == b"s"
    assert bytes(buffer.pop(7)) == b"spamegg"


def test_ringbuffer_reset():
    buffer = RingBuffer(format="B", capacity=5)
    buffer.push(b"hello")
    buffer.reset()
    assert buffer.pop(5) is None


def test_ringbuffer_invalid():
    with pytest.raises(ValueError):
        RingBuffer(format="B", capacity=0)

    buffer = RingBuffer(format="B", capacity=10)

    # Empty data is okay
    buffer.push(b"")

    buffer.push(b"hello")

    # Can't pop negative or zero
    for i in (-1, 0):
        with pytest.raises(ValueError):
            buffer.pop(i)

    # Types must match
    with pytest.raises(TypeError):
        buffer.push(np.array("f", [1.0]))


def test_concatenate():
    array_size = 1000
    num_arrays = 100
    arrays = [
        Array(
            format="i",
            shape=(array_size,),
            itemsize=struct.calcsize("i"),
        )
        for i in range(num_arrays)
    ]
    expected = [
        np.linspace(i, i + array_size, num=array_size, dtype="i")
        for i in range(
            0,
            array_size * num_arrays,
            array_size,
        )
    ]
    for i, arr in enumerate(arrays):
        arr[:] = expected[i]

    concatenated = concatenate(*arrays)
    assert np.array_equal(
        np.array(concatenated, dtype="i"),
        np.concatenate(expected),
    )


def test_concatenate_valueerror_ndims():
    with pytest.raises(ValueError):
        concatenate(
            np.array([[1, 2], [3, 4]]),
            np.array([[1, 2], [3, 4]]),
        )


def test_concatenate_valueerror_no_args():
    with pytest.raises(ValueError):
        concatenate()


@pytest.mark.parametrize(
    "invalid",
    (
        np.array([1.1, 2.2], dtype="f"),
        b"hello",
    ),
)
def test_concatenate_typeerror(invalid):
    with pytest.raises(TypeError):
        concatenate(invalid, np.array([1, 2], dtype="i"))


def test_concatenate_valueerror_empty():
    with pytest.raises(ValueError):
        concatenate(b"")


def test_callback_void_ptr():
    _test_callback_void_ptr()
