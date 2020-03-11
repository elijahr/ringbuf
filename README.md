# ringbuf
A fast, lock free, ring buffer for Python, written in Cython and based on [ContiguousRingbuffer](https://github.com/tlouwers/embedded/blob/master/ContiguousBuffer/ContiguousRingbuffer.hpp) by tlouwers.

![build_status](https://travis-ci.org/elijahr/ringbuf.svg?branch=master)

## Installation

```shell
pip install ringbuf
```

## Usage

See the [tests](https://github.com/elijahr/aiolo/blob/master/tests/main.py).

## Supported platforms

Travis CI tests with the following configurations:
* Ubuntu 18.04 Bionic Beaver + [CPython3.6, CPython3.7, CPython3.8, PyPy7.3.0 (3.6.9)]
* OS X + [CPython3.6, CPython3.7, CPython3.8, PyPy7.3.0 (3.6.9)]

## Contributing

Pull requests are welcome, please file any issues you encounter.
