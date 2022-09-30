import os
import platform

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
extra_compile_args = []
extra_link_args = []


if boost_root := os.environ.get("BOOST_ROOT"):
    # Try to find the include dir
    headers = (
        os.path.join(boost_root, "boost", "lockfree", "spsc_queue.hpp"),
        os.path.join(boost_root, "include", "boost", "lockfree", "spsc_queue.hpp"),
    )
    for header in headers:
        if os.path.exists(header):
            include_dir = os.path.join(*header.split(os.path.sep)[:-3])
            include_dirs.append(include_dir)
            extra_compile_args.append(f"-I{include_dir}")
            break
    else:
        raise ValueError(f"Could not find include directory in {boost_root}")

    link_flag = "/LIBPATH:" if platform.system() == "Windows" else "-L"
    lib_dirs = (
        os.path.join(boost_root, "lib"),
        os.path.join(boost_root, "lib64"),
        os.path.join(boost_root, "lib32"),
    )
    for lib_dir in lib_dirs:
        if os.path.exists(lib_dir):
            extra_link_args.append(f"{link_flag}{lib_dir}")
            break
    else:
        raise ValueError(f"Could not find lib directory in {boost_root}")

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
                extra_compile_args=extra_compile_args,
                extra_link_args=extra_link_args,
                libraries=["boost_system"],
                include_dirs=include_dirs,
            ),
        ],
        gdb_debug=compile_time_env["DEBUG"],
        compile_time_env=compile_time_env,
        compiler_directives={"language_level": 3},
    ),
)
