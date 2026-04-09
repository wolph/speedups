"""Low-level ASCII STL I/O used internally by numpy-stl.

For reading and writing STL files, use numpy-stl:
https://github.com/WoLpH/numpy-stl
"""

import typing

import numpy as np
import numpy.typing as npt

dtype: typing.Final[np.dtype[typing.Any]]

def ascii_read(
    fh: typing.IO[bytes],
    buf: bytes,
) -> tuple[bytes, npt.NDArray[np.void]]:
    """Read ASCII STL data from a file handle.

    Args:
        fh: The file handle to read from.
        buf: A buffer to read data into.

    Returns:
        A tuple of (remaining_buffer, numpy_array_of_facets).
    """
    ...

def ascii_write(
    fh: typing.IO[bytes],
    name: bytes,
    arr: npt.NDArray[np.void],
) -> None:
    """Write ASCII STL data to a file handle.

    Args:
        fh: The file handle to write to.
        name: The name of the solid.
        arr: The numpy array containing facet data.
    """
    ...
