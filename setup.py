import argparse
import glob
import itertools
import os
import sys

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install


try:
    import __pypy__
except ImportError:
    __pypy__ = None


try:
    from Cython.Build.Dependencies import cythonize
except ImportError:
    import subprocess

    errno = subprocess.call([sys.executable, '-m', 'pip', 'install', 'cython'])
    if errno:
        print('Please install the cython package')
        raise SystemExit(errno)
    else:
        from Cython.Build.Dependencies import cythonize


DIR = os.path.dirname(__file__)
MODULE_PATH = os.path.join(DIR, 'src', 'ringbuf')
EMBEDDED_PATH = os.path.join(DIR, 'src', 'embedded')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    return parser.parse_known_args(sys.argv)[0]


def get_cython_compile_time_env(defaults=None):
    env = dict(**defaults or {})
    env.update({
        'PYPY': __pypy__ is not None
    })
    return env


class BuildExt(build_ext):
    user_options = build_ext.user_options + []

    def initialize_options(self):
        self.single_version_externally_managed = False
        build_ext.initialize_options(self)
        args = get_args()
        self.debug = args.debug
        self.single_version_externally_managed = False

    def finalize_options(self):
        self.single_version_externally_managed = False
        build_ext.finalize_options(self)
        self.single_version_externally_managed = False


class Install(install):
    user_options = install.user_options + [
        ('debug', None, 'Build with debug symbols'),
    ]

    def initialize_options(self):
        self.single_version_externally_managed = False
        install.initialize_options(self)
        args = get_args()
        self.debug = args.debug
        self.single_version_externally_managed = False

    def finalize_options(self):
        self.single_version_externally_managed = False
        install.finalize_options(self)
        self.single_version_externally_managed = False


def get_readme():
    with open('README.md', 'r') as fh:
        return fh.read()


def get_packages():
    args = get_args()
    packages = ['ringbuf']
    return packages


def get_package_dir():
    args = get_args()
    package_dir = {'ringbuf': MODULE_PATH}
    return package_dir


def get_package_data():
    package_data = {'ringbuf': ['*.pyx', '*.pxd']}
    return package_data


def get_ext_modules():
    args = get_args()
    ext_modules = []
    include_dirs = [os.path.abspath(d) for d in (DIR, MODULE_PATH, EMBEDDED_PATH)]

    for path in itertools.chain(
            glob.glob(os.path.join(MODULE_PATH, '*.pyx'))):
        module_name = path.replace(MODULE_PATH, 'ringbuf').replace('/', '.').replace('.pyx', '')
        sources = [path]
        # headers = []
        extra_compile_args = []
        extra_link_args = []

        if module_name == 'ringbuf.ringbuf':
            # headers.append(os.path.join(EMBEDDED_PATH, 'RingBuffer', 'ContiguousRingbuffer.hpp'))
            extra_compile_args += ['-std=c++11']
            extra_link_args += ['-std=c++11']

        ext_modules.append(Extension(
            module_name,
            sources=sources,
            # headers=headers,
            include_dirs=include_dirs,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
        ))

    compile_time_env = get_cython_compile_time_env(
        defaults=dict(DEBUG=args.debug))
    ext_modules = cythonize(
        ext_modules,
        gdb_debug=args.debug,
        compile_time_env=compile_time_env,
        compiler_directives=dict(
            language_level=3
        ),
    )
    return ext_modules


setup(
    name='ringbuf',
    version='1.0.2',
    description='A fast, lock free, ring buffer for Python.',
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    url='https://github.com/elijahr/ringbuf',
    author='Elijah Shaw-Rutschman',
    author_email='elijahr@gmail.com',
    packages=get_packages(),
    package_dir=get_package_dir(),
    package_data=get_package_data(),
    cmdclass={
        'build_ext': BuildExt,
        'install': Install,
    },
    ext_modules=get_ext_modules(),
    setup_requires=['cython'],
    extras_require={
        'test': [
            'numpy',
            'pytest',
        ],
    },
    classifiers=[
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: BSD License',
    ],
)
