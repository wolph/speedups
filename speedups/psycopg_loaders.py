"""Custom PostgreSQL binary loaders for NumPy integration.

This module provides efficient ways to load PostgreSQL arrays directly into
NumPy arrays using Cython-optimized conversion functions.
"""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import typing

import numpy as np
import numpy.typing as npt
import psycopg
import psycopg.abc
import psycopg.types.array

import speedups.psycopg_array

T = typing.TypeVar('T')
ConverterT: typing.TypeAlias = typing.Callable[
    [memoryview, npt.NDArray[typing.Any]], None
]

_SUPPORTED_TYPES: typing.Final[tuple[str, ...]] = (
    'float4',
    'float8',
    'smallint',
    'integer',
    'bigint',
)


class NumpyLoader(psycopg.types.array.ArrayBinaryLoader):
    """A binary loader for PostgreSQL arrays that returns NumPy arrays.

    This loader bypasses standard Python object creation for array elements
    by using optimized Cython functions to fill a pre-allocated NumPy array.
    """

    @classmethod
    def install(
        cls,
        cursor: psycopg.AsyncCursor[T] | psycopg.Cursor[T],
    ) -> None:
        """Register the NumpyLoader for all supported array types.

        Args:
            cursor: The psycopg cursor to register the loader with.

        Raises:
            KeyError: If a required adapter type is not found.
        """
        for type_ in _SUPPORTED_TYPES:
            adapter_type = cursor.adapters.types.get(f'{type_}[]')
            if adapter_type is None:
                raise KeyError(f'Adapter type not found: {type_}[]')
            cursor.adapters.register_loader(adapter_type.array_oid, cls)

    def load(  # type: ignore[override]
        self,
        data: memoryview,
    ) -> npt.NDArray[typing.Any]:
        """Load the binary PostgreSQL array data into a NumPy array.

        Args:
            data: The raw binary data from PostgreSQL.

        Returns:
            A NumPy array containing the decoded data.

        Raises:
            TypeError: If the loader type is unsupported.
        """
        assert isinstance(data, memoryview)

        struct_head = psycopg.types.array._struct_head
        struct_dim = psycopg.types.array._struct_dim

        rows, _, oid = struct_head.unpack_from(data)
        if rows:
            # Move 'pointer' beyond header
            data = data[struct_head.size :]
        else:
            return np.empty(0)

        # Read dimensions
        dimensions_size = struct_dim.size * rows
        dimensions: list[int] = []
        for dimension, lbound in struct_dim.iter_unpack(
            data[:dimensions_size]
        ):
            assert lbound == 1, 'Lower bound other than 1 is not supported'
            dimensions.append(dimension)

        # Move 'pointer' beyond dimension headers
        data = data[dimensions_size:]

        loader: psycopg.abc.Loader = self._tx.get_loader(oid, self.format)
        loader_name: str = loader.__class__.__name__
        dtype: type[np.generic]

        match loader_name:
            case name if name.startswith('Float4'):
                dtype = np.float32
            case name if name.startswith('Float8'):
                dtype = np.float64
            case name if name.startswith('Int2'):
                dtype = np.int16
            case name if name.startswith('Int4'):
                dtype = np.int32
            case name if name.startswith('Int8'):
                dtype = np.int64
            case _:
                raise TypeError(f'Unsupported loader type: {loader_name}')

        # Create numpy output array
        output: npt.NDArray[typing.Any] = np.empty(dimensions, dtype=dtype)

        # Convert data to numpy array
        converter: ConverterT
        if loader_name.startswith('Float'):
            converter = speedups.psycopg_array.float_array_to_numpy
        else:
            converter = speedups.psycopg_array.int_array_to_numpy

        # Convert and fill the array
        converter(data.cast('c'), output.reshape(-1))  # type: ignore[arg-type]

        return output
