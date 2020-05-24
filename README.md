# ringbuf

A lock-free, single-producer, single-consumer, ring buffer for Python and Cython.

![build_status](https://travis-ci.org/elijahr/ringbuf.svg?branch=master)

## Installation

OS X: `brew install boost`

Ubuntu: `apt-get install libboost-all-dev`

Windows: Install the latest version of [`Boost`](https://www.boost.org/) then set the `BOOST_ROOT` environment variable to point to its folder.

Then:

```shell
pip install ringbuf
```

## Motivation

When working with realtime DSP in Python, we might be wrapping some external C/C++ library (for instance, PortAudio) which runs some user-provided callback function in realtime. The callback function shouldn't allocate/deallocate memory, shouldn't contain any critical sections (mutexes), and so forth, to prevent priority inversion. If the callback were to contain Python objects, we'd likely be allocating and deallocating, and at the very least, acquiring and releasing the GIL. So, the callback cannot interact with Python objects if we expect realtime performance. As such, there's a need for buffering data in a non-locking way between a C/C++ callback and Python.

Enter ringbuf, Cython wrappers for [`boost::lockfree::spsc_queue`](https://www.boost.org/doc/libs/1_72_0/doc/html/boost/lockfree/spsc_queue.html). Our Python code can read from and write to a `ringbuf.RingBuffer` object, and our C++ code can read from and write to that buffer's underlying `spsc_queue`, no GIL required.

## Usage

Any Python object which supports the [buffer protocol](https://docs.python.org/3/c-api/buffer.html) can be stored in `ringbuf.RingBuffer`. This includes, but is not limited to: `bytes`, `bytearray`, `array.array`, and `numpy.ndarray`.

### NumPy

```python
import numpy as np
from ringbuf import RingBuffer

buffer = RingBuffer(format='f', capacity=100)

data = np.linspace(-1, 1, num=100, dtype='f')

buffer.push(data)

popped = buffer.pop(100)

assert np.array_equal(data, popped)
```

### bytes

```python
from ringbuf import RingBuffer

buffer = RingBuffer(format='B', capacity=11)

buffer.push(b'hello world')

popped = buffer.pop(11)

assert bytes(popped) == b'hello world'
```

### Interfacing with C/C++

mymodule.pxd:

```cython
# distutils: language = c++
cdef void callback(void* q)
```

mymodule.pyx:

```cython
# distutils: language = c++
from array import array

from ringbuf.boost cimport spsc_queue, void_ptr_to_spsc_queue_char_ptr
from ringbuf.ringbuf cimport RingBuffer

from some_c_library cimport some_c_function


cdef void callback(void* q):
    cdef:
        # Cast the void* back to an spsc_queue.
        # The underlying queue always holds chars.
        spsc_queue[char] *queue = void_ptr_to_spsc_queue_char_ptr(q)
        double[5] to_push = [1.0, 2.0, 3.0, 4.0, 5.0]

    # Since the queue holds chars, you'll have to cast and adjust size accordingly.
    queue.push(<char*>to_push, sizeof(double) * 5)


def do_stuff():
    cdef:
        RingBuffer buffer = RingBuffer(format='d', capacity=100)
        void* queue = buffer.queue_void_ptr()

    # Pass our callback and a void pointer to the buffer's queue to some third party library.
    # Presumably, the C library schedules the callback and passes it the queue's void pointer.
    some_c_function(callback, queue)

    sleep(1)

    assert array.array('d', buffer.pop(5)) == array.array('d', range(1, 6))
```

### Handling overflow & underflow

When `RingBuffer.push()` overflows, it returns the data that couldn't be pushed (or None, if all was pushed):

```python
from ringbuf import RingBuffer

buffer = RingBuffer(format='B', capacity=10)
overflowed = buffer.push(b'spam eggs ham')
assert overflowed == b'ham'
```

When `RingBuffer.pop()` underflows, it returns whatever data could be popped:

```python
from ringbuf import RingBuffer

buffer = RingBuffer(format='B', capacity=13)
buffer.push(b'spam eggs ham')
popped = buffer.pop(buffer.capacity * 100)
assert bytes(popped) == b'spam eggs ham'
```



For additional usage see the [tests](https://github.com/elijahr/ringbuf/blob/master/test.py).

## Supported platforms

Travis CI tests with the following configurations:
* Ubuntu 18.04 Bionic Beaver:
   * CPython3.6
   * CPython3.7
   * CPython3.8
   * PyPy7.3.0 (3.6.9)
* OS X:
    * CPython3.6
    * CPython3.7
    * CPython3.8
    * PyPy7.3.0 (3.6.9)

Any platform with a C++11 compiler will probably work. Windows support has been added, but it is considered
experimental. A pull request to test ringbuf on Windows for Travis CI would be most welcome.

## Contributing

Pull requests are welcome, please file any issues you encounter.

## Changelog

### v2.5.0 2020-04-17
* Added experimental support for Windows.

### v2.4.0 2020-03-23
* Added `RingBuffer.reset()` method to clear the buffer.

### v2.3.0 2020-03-22
* Added `concatenate` function for joining multiple arbitrary Python objects that support the buffer protocol.