"""Metadata information for the speedups package.

This module contains package-wide constants such as the version, author,
and description.
"""

import importlib.metadata
import typing

__package_name__: typing.Final[str] = 'speedups'
__import_name__: typing.Final[str] = 'speedups'

try:
    __version_raw__ = importlib.metadata.version(__package_name__)
except importlib.metadata.PackageNotFoundError:
    __version_raw__ = '0.0.0'

__version__: typing.Final[str] = __version_raw__

__author__: typing.Final[str] = 'Rick van Hattem, Joren Hammudoglu'
__author_email__: typing.Final[str] = 'Wolph@Wol.ph, jhammudoglu@gmail.com'
__description__: typing.Final[str] = (
    'Library with some C and Cython code for speeding up'
    ' common operations. This is externalized to avoid the'
    ' hassle of building binary wheels in my other projects.'
)
__url__: typing.Final[str] = 'https://github.com/WoLpH/speedups/'
