"""Low-level array to numpy conversion functions.

These are used internally to speed up PostgreSQL array decoding.
"""

import collections.abc
import typing

import numpy as np
import numpy.typing as npt

ConverterT: typing.TypeAlias = collections.abc.Callable[
    [memoryview, npt.NDArray[typing.Any]], None
]

def float_array_to_numpy(
    data: memoryview,
    output_view: npt.NDArray[np.floating[typing.Any]],
) -> None:
    """Convert a memoryview of float data to a numpy array.

    Args:
        data: The input memoryview of data to convert.
        output_view: The output numpy array view.
    """
    ...

def int_array_to_numpy(
    data: memoryview,
    output_view: npt.NDArray[np.integer[typing.Any]],
) -> None:
    """Convert a memoryview of integer data to a numpy array.

    Args:
        data: The input memoryview of data to convert.
        output_view: The output numpy array view.
    """
    ...
