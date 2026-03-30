# pyright: reportPrivateUsage=false
from __future__ import annotations

import typing

import numpy as np
import numpy.typing as npt
from psycopg.types import array as psycopg_array

if typing.TYPE_CHECKING:
    import psycopg
    from psycopg.abc import Loader

import speedups.psycopg_array

T = typing.TypeVar('T')
ConverterT = typing.Callable[[memoryview, npt.NDArray[typing.Any]], None]


class NumpyLoader(psycopg_array.ArrayBinaryLoader):
    @classmethod
    def install(
        cls,
        cursor: psycopg.AsyncCursor[T] | psycopg.Cursor[T],
    ):
        types = (
            'float4',
            'float8',
            'smallint',
            'integer',
            'bigint',
        )

        for type_ in types:
            adapter_type = cursor.adapters.types.get(f'{type_}[]')
            if adapter_type is None:
                raise KeyError(f'Adapter type not found: {type_}[]')
            cursor.adapters.register_loader(adapter_type.array_oid, cls)

    def load(  # type: ignore[override]
        self,
        data: memoryview,
    ) -> npt.NDArray[typing.Any]:
        assert isinstance(data, memoryview)

        struct_head = psycopg_array._struct_head
        struct_dim = psycopg_array._struct_dim

        rows, _, oid = struct_head.unpack_from(data)
        if rows:
            # Move "pointer" beyond header
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

        # Move "pointer" beyond dimension headers
        data = data[dimensions_size:]

        loader: Loader = self._tx.get_loader(oid, self.format)
        loader_name = loader.__class__.__name__
        dtype: type[np.generic]
        if loader_name.startswith('Float4'):
            dtype = np.float32
        elif loader_name.startswith('Float8'):
            dtype = np.float64
        elif loader_name.startswith('Int2'):
            dtype = np.int16
        elif loader_name.startswith('Int4'):
            dtype = np.int32
        elif loader_name.startswith('Int8'):
            dtype = np.int64
        else:
            raise TypeError(f'Unsupported loader type: {loader_name}')

        # Create numpy output array
        output: npt.NDArray[typing.Any] = np.empty(dimensions, dtype=dtype)

        # Convert data to numpy array
        converter: ConverterT
        if loader_name.startswith('Float'):
            converter = speedups.psycopg_array.float_array_to_numpy
        else:
            converter = speedups.psycopg_array.int_array_to_numpy

        converter(data.cast('c'), output.reshape(-1))  # type: ignore[arg-type]

        return output
