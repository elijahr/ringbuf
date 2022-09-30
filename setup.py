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


def find_spsc_queue_hpp(boost_root):
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
            yield header


def find_boost_system_lib_msvc(boost_root):
    for lib_dir in itertools.chain.from_iterable(
        map(
            glob.glob,
            (
                os.path.join(boost_root, "lib"),
                os.path.join(boost_root, "lib64"),
                os.path.join(boost_root, "lib64-*"),
                os.path.join(boost_root, "lib32"),
                os.path.join(boost_root, "lib32-*"),
            ),
        )
    ):
        for lib in itertools.chain.from_iterable(
            map(
                glob.glob,
                (
                    # Prefer multi-threaded
                    os.path.join(lib_dir, "boost_system-*mt*.dll"),
                    os.path.join(lib_dir, "libboost_system-*mt*.dll"),
                    os.path.join(lib_dir, "boost_system-*.dll"),
                    os.path.join(lib_dir, "libboost_system-*.dll"),
                    os.path.join(lib_dir, "boost_system.dll"),
                    os.path.join(lib_dir, "libboost_system.dll"),
                ),
            )
        ):
            yield lib


def find_boost_system_lib_unix(boost_root):
    for lib_dir in itertools.chain.from_iterable(
        map(
            glob.glob,
            (
                os.path.join(boost_root, "lib"),
                os.path.join(boost_root, "lib64"),
                os.path.join(boost_root, "lib32"),
                os.path.join(boost_root, "lib", "**"),
            ),
        )
    ):
        for ext in (
            "so",  # shared on Linux, BSD
            "dylib",  # shared on macOS
        ):
            for lib in itertools.chain.from_iterable(
                map(
                    glob.glob,
                    (
                        # Prefer multi-threaded
                        os.path.join(lib_dir, f"libboost_system-*mt*.{ext}"),
                        os.path.join(lib_dir, f"libboost_system-*.{ext}"),
                        os.path.join(lib_dir, f"libboost_system.{ext}"),
                    ),
                )
            ):
                yield lib


class build_ext_compiler_check(build_ext):
    def build_extensions(self):
        compiler_type = self.compiler.compiler_type  # usually "unix" or "msvc"

        boost_root = os.environ.get("BOOST_ROOT")
        if boost_root:
            ringbufcy_ext = [e for e in self.extensions if e.name == "ringbuf.ringbufcy"][0]

            # Try to find the include dir
            for header in find_spsc_queue_hpp(boost_root):
                include_dir = os.path.join(*header.split(os.path.sep)[:-3])
                ringbufcy_ext.include_dirs.append(include_dir)
                ringbufcy_ext.extra_compile_args.append(f"-I{include_dir}")
                break
            else:
                raise ValueError(f"Could not find boost/lockfree/spsc_queue.hpp in BOOST_ROOT ({boost_root})")

            # Try to find the library dir
            if compiler_type == "msvc":
                for lib in find_boost_system_lib_msvc(boost_root):
                    lib_dir = os.path.dirname(lib)
                    ringbufcy_ext.extra_link_args.append(f"/LIBPATH:{lib_dir}")
                    lib_name = os.path.splitext(os.path.basename(lib))[0]
                    ringbufcy_ext.libraries = [lib_name]
                    break
                else:
                    raise ValueError(f"Could not find boost_system library in BOOST_ROOT ({boost_root})")
            else:
                for lib in find_boost_system_lib_unix(boost_root):
                    lib_dir = os.path.dirname(lib)
                    ringbufcy_ext.extra_link_args.append(f"-L{lib_dir}")
                    lib_name = os.path.splitext(os.path.basename(lib))[0]
                    # remove lib prefix
                    lib_name = lib_name[3:]
                    ringbufcy_ext.libraries = [lib_name]
                    break
                else:
                    raise ValueError(f"Could not find boost_system library in BOOST_ROOT ({boost_root})")

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
