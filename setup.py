import os

from Cython.Build import (
    cythonize,
)
from setuptools import (
    Extension,
    setup,
)

compile_time_env = {
    "DEBUG": os.environ.get("DEBUG") in ("1", "yes", "true", "y"),
    "PYPY": False,
}

try:
    import __pypy__  # pylint: disable=unused-import

    compile_time_env["PYPY"] = True
except ImportError:
    ...

include_dirs = []

if os.environ.get("BOOST_ROOT"):
    include_dirs.insert(0, os.environ["BOOST_ROOT"])

setup(
    ext_modules=cythonize(
        [
            Extension(
                "ringbuf.libc_constants",
                sources=["ringbuf/libc_constants.pyx"],
                language="c",
            ),
            Extension(
                "ringbuf.ringbufcy",
                sources=["ringbuf/ringbufcy.pyx"],
                language="c++",
                extra_compile_args=["-std=c++11"],
                extra_link_args=["-std=c++11"],
                libraries=["boost_system"],
                include_dirs=include_dirs,
            ),
        ],
        gdb_debug=compile_time_env["DEBUG"],
        compile_time_env=compile_time_env,
        compiler_directives={"language_level": 3},
    ),
)
