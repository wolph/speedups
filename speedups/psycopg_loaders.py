import numpy as np
import psycopg
import speedups.psycopg_array
from psycopg import _struct as psycopg_struct  # noqa
from psycopg.abc import Loader
from psycopg.types import array as psycopg_array


class NumpyLoader(psycopg_array.ArrayBinaryLoader):

    @classmethod
    def install(cls, cursor: psycopg.AsyncCursor | psycopg.Cursor):
        types = 'float4', 'float8', 'smallint', 'integer', 'bigint',

        for type_ in types:
            cursor.adapters.register_loader(
                cursor.adapters.types.get(f'{type_}[]').array_oid,
                cls,
            )

    def load(self, data: memoryview):
        assert isinstance(data, memoryview)

        struct_head = psycopg_array._struct_head
        struct_dim = psycopg_array._struct_dim

        rows, data_offset, oid = struct_head.unpack_from(data)
        if rows:
            # Move "pointer" beyond header
            data = data[struct_head.size:]
        else:
            return []

        # Read dimensions
        dimensions_size = struct_dim.size * rows
        dimensions = []
        for dimension, lbound in struct_dim.iter_unpack(data[:dimensions_size]):
            assert lbound == 1, 'Lower bound other than 1 is not supported'
            dimensions.append(dimension)

        # Move "pointer" beyond dimension headers
        data = data[dimensions_size:]

        loader: Loader = self._tx.get_loader(oid, self.format)
        loader_name = loader.__class__.__name__
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
        output = np.empty(dimensions, dtype=dtype)

        # Convert data to numpy array
        if loader_name.startswith('Float'):
            converter = speedups.psycopg_array.float_array_to_numpy
        else:
            converter = speedups.psycopg_array.int_array_to_numpy

        converter(data.cast('c'), output.reshape(-1))
        return output
