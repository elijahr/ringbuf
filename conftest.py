import sys

# Don't attempt a relative import of ringbuf when running tests
sys.path = sys.path[1:]
