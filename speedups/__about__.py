from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

__package_name__ = 'speedups'
__import_name__ = 'speedups'

try:
    __version__: str = _version(__package_name__)
except PackageNotFoundError:
    __version__ = '0.0.0'

__author__ = 'Rick van Hattem, Joren Hammudoglu'
__author_email__ = 'Wolph@Wol.ph, jhammudoglu@gmail.com'
__description__ = (
    'Library with some C and Cython code for speeding up'
    ' common operations. This is externalized to avoid the'
    ' hassle of building binary wheels in my other projects.'
)
__url__ = 'https://github.com/WoLpH/speedups/'
