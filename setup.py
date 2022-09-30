import glob
import itertools
import os

from Cython.Build import (
    cythonize,
)
from setuptools import (
    Extension,
    setup,
)
from setuptools.command.build_ext import (
    build_ext,
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


class build_ext_compiler_check(build_ext):
    def build_extensions(self):
        compiler_type = self.compiler.compiler_type  # usually "unix" or "msvc"

        if boost_root := os.environ.get("BOOST_ROOT"):
            ringbufcy_ext = [e for e in self.extensions if e.name == "ringbuf.ringbufcy"][0]

            # Try to find the include dir
            for header in (
                os.path.join(
                    boost_root,
                    "boost",
                    "lockfree",
                    "spsc_queue.hpp",
                ),
                os.path.join(
                    boost_root,
                    "include",
                    "boost",
                    "lockfree",
                    "spsc_queue.hpp",
                ),
            ):
                if os.path.exists(header):
                    include_dir = os.path.join(*header.split(os.path.sep)[:-3])
                    ringbufcy_ext.include_dirs.append(include_dir)
                    ringbufcy_ext.extra_compile_args.append(f"-I{include_dir}")
                    break
            else:
                raise ValueError(f"Could not find headers with BOOST_ROOT={boost_root}")

            # Try to find the library dir
            for lib_dir in itertools.chain.from_iterable(
                map(
                    glob.glob,
                    (
                        os.path.join(boost_root, "lib"),
                        os.path.join(boost_root, "lib64"),
                        os.path.join(boost_root, "lib32"),
                        os.path.join(boost_root, "lib64-*"),
                        os.path.join(boost_root, "lib32-*"),
                    ),
                )
            ):
                if os.path.exists(lib_dir) and os.path.isdir(lib_dir):
                    link_flag = "/LIBPATH:" if compiler_type == "msvc" else "-L"
                    ringbufcy_ext.extra_link_args.append(f"{link_flag}{lib_dir}")
                    break
            else:
                raise ValueError(f"Could not find libraries with BOOST_ROOT={boost_root}")

        build_ext.build_extensions(self)


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
                libraries=["boost_system"],
            ),
        ],
        gdb_debug=compile_time_env["DEBUG"],
        compile_time_env=compile_time_env,
        compiler_directives={"language_level": 3},
    ),
    cmdclass={"build_ext": build_ext_compiler_check},
)
