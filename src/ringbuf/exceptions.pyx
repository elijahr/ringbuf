

__all__ = ['ContiguousBufferError', 'Overflow', 'Underflow']


class ContiguousBufferError(Exception):
    ...


class Overflow(ContiguousBufferError):
    ...


class Underflow(ContiguousBufferError):
    ...
