import argparse
import glob
import itertools
import os
import sys

from setuptools import (
    Extension,
    setup,
)
from setuptools.command.build_ext import (
    build_ext,
)
from setuptools.command.install import (
    install,
)

try:
    import __pypy__
except ImportError:
    __pypy__ = None


try:
    from Cython.Build.Dependencies import (
        cythonize,
    )
except ImportError as exc:
    import subprocess

    errno = subprocess.call([sys.executable, "-m", "pip", "install", "cython"])
    if errno:
        print("Please install the cython package")
        raise SystemExit(errno) from exc
    from Cython.Build.Dependencies import (
        cythonize,
    )


DIR = os.path.dirname(__file__)
MODULE_PATH = os.path.join(DIR, "ringbuf")
INCLUDE_DIRS = [os.path.abspath(d) for d in (DIR, MODULE_PATH)]

try:
    INCLUDE_DIRS.insert(0, os.environ["BOOST_ROOT"])
except KeyError as exc:
    if os.name == "nt":
        raise KeyError(
            'Please install Boost and specify its location using the "BOOST_ROOT" environmental variable'
        ) from exc


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    return parser.parse_known_args(sys.argv)[0]


def get_cython_compile_time_env(defaults=None):
    env = dict(**defaults or {})
    env.update({"PYPY": __pypy__ is not None})
    return env


class BuildExt(build_ext):
    user_options = build_ext.user_options + []

    def initialize_options(self):
        build_ext.initialize_options(self)
        args = get_args()
        self.debug = args.debug


class Install(install):
    user_options = install.user_options + [
        ("debug", None, "Build with debug symbols"),
    ]

    def initialize_options(self):
        install.initialize_options(self)
        args = get_args()
        self.debug = args.debug


def get_readme():
    with open("README.md", "r", encoding="utf8") as fh:
        return fh.read()


def get_packages():
    packages = ["ringbuf"]
    return packages


def get_package_dir():
    package_dir = {"ringbuf": MODULE_PATH}
    return package_dir


def get_package_data():
    package_data = {"ringbuf": ["*.pyx", "*.pxd"]}
    return package_data


def get_ext_modules():
    args = get_args()
    ext_modules = []

    for path in itertools.chain(glob.glob(os.path.join(MODULE_PATH, "*.pyx"))):
        module_name = path.replace(MODULE_PATH, "ringbuf").replace(os.path.sep, ".").replace(".pyx", "")
        sources = [path]
        extra_compile_args = []
        extra_link_args = []
        libraries = []

        if module_name == "ringbuf.ringbuf":
            extra_compile_args += ["-std=c++11"]
            extra_link_args += ["-std=c++11"]
            libraries += ["boost_system"]

        ext_modules.append(
            Extension(
                module_name,
                sources=sources,
                include_dirs=INCLUDE_DIRS,
                extra_compile_args=extra_compile_args,
                extra_link_args=extra_link_args,
                libraries=libraries,
            )
        )

    compile_time_env = get_cython_compile_time_env(defaults=dict(DEBUG=args.debug))
    ext_modules = cythonize(
        ext_modules,
        gdb_debug=args.debug,
        compile_time_env=compile_time_env,
        compiler_directives=dict(language_level=3),
    )
    return ext_modules


setup(
    packages=get_packages(),
    package_dir=get_package_dir(),
    package_data=get_package_data(),
    cmdclass={
        "build_ext": BuildExt,
        "install": Install,
    },
    ext_modules=get_ext_modules(),
)
