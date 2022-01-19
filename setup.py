import os
import pathlib

import numpy
import setuptools
from Cython.Build import cythonize

# Get current directory
PATH = pathlib.Path(__file__).parent
SRC_PATH = PATH / 'speedups'

# Tell the compiler to optimize
os.environ.setdefault('CFLAGS', '-O3')

# To prevent importing about and thereby breaking the coverage info we use this
# exec hack
about = {}
with (SRC_PATH / '__about__.py').open() as fh:
    exec(fh.read(), about)


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
        name=about['__package_name__'],
        author=about['__author__'],
        author_email=about['__author_email__'],
        description=about['__description__'],
        url=about['__url__'],
        ext_modules=cythonize([
            create_extension('speedups.psycopg_array'),
        ], language_level=3),
    )
