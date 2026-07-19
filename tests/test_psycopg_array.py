"""Direct tests for the low-level binary array converters.

These call the Cython converters with hand-crafted PostgreSQL binary
element streams, so they need no PostgreSQL server. Each element is a
4-byte big-endian size header followed by that many payload bytes.
"""

from __future__ import annotations

import struct
import typing

import numpy as np
import pytest

from speedups import psycopg_array


def _elements(*values: bytes) -> memoryview[typing.Any]:
    """Encode payloads as a PostgreSQL binary array element stream."""
    data: bytes = b''.join(
        struct.pack('!i', len(value)) + value for value in values
    )
    return memoryview(data).cast('c')


def test_float_array_decodes_float4_and_float8() -> None:
    data = _elements(struct.pack('!f', 1.5), struct.pack('!d', -2.25))
    output: np.ndarray = np.empty(2, dtype=np.float64)
    psycopg_array.float_array_to_numpy(data, output)
    assert output.tolist() == [1.5, -2.25]


def test_float_array_null_becomes_nan() -> None:
    data = memoryview(struct.pack('!i', -1) + struct.pack('!if', 4, 3.0)).cast(
        'c'
    )
    output: np.ndarray = np.empty(2, dtype=np.float32)
    psycopg_array.float_array_to_numpy(data, output)
    assert np.isnan(output[0])
    assert output[1] == 3.0


def test_int_array_decodes_all_sizes() -> None:
    data = _elements(
        struct.pack('!h', 3),
        struct.pack('!i', -4),
        struct.pack('!q', 5),
    )
    output: np.ndarray = np.empty(3, dtype=np.int64)
    psycopg_array.int_array_to_numpy(data, output)
    assert output.tolist() == [3, -4, 5]


def test_int_array_null_raises() -> None:
    data = memoryview(struct.pack('!i', -1)).cast('c')
    output: np.ndarray = np.empty(1, dtype=np.int32)
    with pytest.raises(ValueError, match='NULL values are not supported'):
        psycopg_array.int_array_to_numpy(data, output)


def test_truncated_element_header_raises() -> None:
    data = memoryview(b'\x00\x00').cast('c')
    output: np.ndarray = np.empty(1, dtype=np.int32)
    with pytest.raises(ValueError, match='truncated element header'):
        psycopg_array.int_array_to_numpy(data, output)


def test_truncated_element_payload_raises() -> None:
    data = memoryview(struct.pack('!i', 4) + b'\x00\x00').cast('c')
    output: np.ndarray = np.empty(1, dtype=np.int32)
    with pytest.raises(ValueError, match='truncated element'):
        psycopg_array.int_array_to_numpy(data, output)


def test_missing_trailing_element_raises() -> None:
    # Output expects two elements but the stream only contains one.
    data = _elements(struct.pack('!f', 1.0))
    output: np.ndarray = np.empty(2, dtype=np.float32)
    with pytest.raises(ValueError, match='truncated element header'):
        psycopg_array.float_array_to_numpy(data, output)


def test_unsupported_element_size_raises() -> None:
    data = _elements(b'abc')
    out_int: np.ndarray = np.empty(1, dtype=np.int32)
    with pytest.raises(TypeError, match='size 3'):
        psycopg_array.int_array_to_numpy(data, out_int)
    out_float: np.ndarray = np.empty(1, dtype=np.float32)
    with pytest.raises(TypeError, match='size 3'):
        psycopg_array.float_array_to_numpy(data, out_float)
