# ringbuf
A fast, lock-free, single-producer, single-consumer, ring buffer for Python.

![build_status](https://travis-ci.org/elijahr/ringbuf.svg?branch=master)

## Installation

```shell
pip install ringbuf
```

## Motivation

When working with realtime DSP in Python, we might be wrapping some external C/C++ library (for instance, PortAudio) which runs some user-provided callback function in realtime. The callback function shouldn't allocate/deallocate memory, shouldn't contain any critical sections (mutexes), and so forth, to prevent priority inversion. If the callback were to contain Python objects, we'd likely be allocating and deallocating, and at the very least, acquiring and releasing the GIL. So, the callback cannot interact with Python objects if we expect realtime performance. As such, there's a need for buffering data in a non-locking way between a C/C++ callback and Python.

Enter ringbuf, Cython wrappers for Terry Louwers' [ContiguousRingbuffer](https://github.com/tlouwers/embedded/blob/master/ContiguousBuffer/ContiguousRingbuffer.hpp), a variant of the [BipBuffer](https://www.codeproject.com/Articles/3479/The-Bip-Buffer-The-Circular-Buffer-with-a-Twist). Our Python code can read from and write to a `ringbuf.RingBuffer` object, and our C/C++ code can read from and write to that buffer's underlying `ContiguousRingbuffer`, no GIL required.

## Usage

### Simple, 1-dimensional array

```python
import numpy as np
from ringbuf import RingBuffer

# Create a buffer to hold 100 floats
buffer = RingBuffer('f', 100)

# Create some data to place in the buffer
data = np.linspace(-1, 1, num=100)

# Fill buffer
with buffer.poke(100) as chunk:
    # chunk is a Cython array, which is similar to a numpy array and supports Python's buffer protocol.
    # We assign data to the chunk using slice syntax.
    chunk[:] = data

# Peek at the buffer
assert np.array_equal(np.array(buffer.peek(100)), data)

# Empty the buffer
assert np.array_equal(buffer.read(100), data)
```

### Multi-dimensional data

```python
import numpy as np
from ringbuf import RingBuffer

# Create a buffer to hold 100 floats
buffer = RingBuffer('f', 100)

# Create some interleaved stereo audio data
data = np.linspace(-1, 1, num=100).reshape((50, 2))

# Fill buffer
with buffer.poke((50, 2)) as chunk:
    # chunk is a Cython array, which is similar to a numpy array and supports Python's buffer protocol.
    # We assign data to the chunk using slice syntax.
    chunk[:] = data

# Peek at the buffer
assert np.array_equal(np.array(buffer.peek((25, 2))), data[:25])
assert np.array_equal(np.array(buffer.peek((50, 2))[25:]), data[25:])

# Empty the buffer
assert np.array_equal(np.array(buffer.read((50, 2))), data)
```

See the [tests](https://github.com/elijahr/ringbuf/blob/master/test.py).

## Supported platforms

Travis CI tests with the following configurations:
* Ubuntu 18.04 Bionic Beaver + [CPython3.6, CPython3.7, CPython3.8, PyPy7.3.0 (3.6.9)]
* OS X + [CPython3.6, CPython3.7, CPython3.8, PyPy7.3.0 (3.6.9)]

Any platforms with a C++11 compiler will probably work.

## Contributing

Pull requests are welcome, please file any issues you encounter.
