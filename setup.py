import os
import pathlib

import numpy
import setuptools
# Get current directory
from Cython.Build import cythonize

PATH = pathlib.Path(__file__).parent
SRC_PATH = PATH / 'speedups'

# Tell the compiler to optimize
os.environ.setdefault('CFLAGS', '-O3')


def create_extension(name, *sources):
    if not sources:
        # if no sources are passed guess from the name
        path = pathlib.Path(*name.split('.'))
        sources = [str(path) + '.pyx']

    return setuptools.Extension(
        name,
        # Extension does not support pathlib yet so we need to convert to str
        [str(source) for source in sources],
        define_macros=[
            ('NPY_NO_DEPRECATED_API', 'NPY_1_7_API_VERSION'),
        ],
        include_dirs=[
            numpy.get_include(),
            str(SRC_PATH),
        ],
    )


if __name__ == '__main__':
    setuptools.setup(
        ext_modules=cythonize([
            create_extension('speedups.psycopg_array'),
        ], language_level=3),
    )
