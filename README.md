# Speedups

[![CI](https://github.com/wolph/speedups/actions/workflows/ci.yml/badge.svg)](https://github.com/wolph/speedups/actions/workflows/ci.yml)
[![Build Wheels](https://github.com/wolph/speedups/actions/workflows/build_wheels.yml/badge.svg)](https://github.com/wolph/speedups/actions/workflows/build_wheels.yml)
[![PyPI](https://img.shields.io/pypi/v/speedups.svg)](https://pypi.org/project/speedups/)
[![Python](https://img.shields.io/pypi/pyversions/speedups.svg)](https://pypi.org/project/speedups/)
[![License](https://img.shields.io/pypi/l/speedups.svg)](https://github.com/WoLpH/speedups/blob/master/LICENSE)

C and Cython extensions for fast STL I/O and PostgreSQL-to-NumPy conversion.

## Performance

Cython extensions run **~3x faster** than pure Python, consistent
across data sizes.

<p align="center">
  <img src="https://raw.githubusercontent.com/wolph/speedups/develop/benchmarks/results/stl_performance.svg" alt="STL I/O Performance" width="700">
</p>

<div align="center">

| Operation | Facets | Pure Python | speedups | Speedup |
|:----------|-------:|------------:|---------:|--------:|
| Write | 10,000 | 28.5 ms | 9.9 ms | **2.9x** |
| Read | 10,000 | 21.6 ms | 7.0 ms | **3.1x** |
| Write | 100,000 | 283.4 ms | 89.3 ms | **3.2x** |
| Read | 100,000 | 218.7 ms | 71.0 ms | **3.1x** |
| Write | 1,000,000 | 2.81 s | 897.5 ms | **3.1x** |
| Read | 1,000,000 | 2.19 s | 711.5 ms | **3.1x** |
| Write | 10,000,000 | 28.62 s | 9.22 s | **3.1x** |
| Read | 10,000,000 | 22.03 s | 7.32 s | **3.0x** |

</div>

<p align="center">
  <img src="https://raw.githubusercontent.com/wolph/speedups/develop/benchmarks/results/pg_array_performance.svg" alt="PostgreSQL COPY to NumPy Performance" width="700">
</p>

<div align="center">

| Type | Elements | Pure Python | speedups | Speedup |
|:-----|:---------|------------:|---------:|--------:|
| int32 | 100K | 7.3 ms | 2.6 ms | **2.8x** |
| int32 | 1M | 73.8 ms | 24.8 ms | **3.0x** |
| int32 | 10M | 747.5 ms | 216.1 ms | **3.5x** |
| int32 | 50M | 3.75 s | 1.05 s | **3.6x** |
| float64 | 100K | 8.0 ms | 3.3 ms | **2.4x** |
| float64 | 1M | 78.3 ms | 32.1 ms | **2.4x** |
| float64 | 10M | 786.5 ms | 268.5 ms | **2.9x** |
| float64 | 50M | 4.01 s | 1.31 s | **3.1x** |

<sub>Benchmarked on Apple M2 Pro, Python 3.14, macOS 15.4. PG data pre-populated in tables to isolate COPY+conversion time. Array dimensionality (1D/2D/3D) has no significant effect on performance.</sub>

</div>

## Install

```bash
pip install speedups
```

With PostgreSQL support:

```bash
pip install speedups[postgres]
```

## PostgreSQL Array → NumPy

Convert PostgreSQL arrays directly to NumPy ndarrays using psycopg's
binary `COPY` protocol. Bypasses Python object creation for a significant
speedup over the default loader.

Supports `float4`, `float8`, `smallint`, `integer`, and `bigint` arrays,
from 1D to N-D.

```python
import psycopg
from speedups.psycopg_loaders import NumpyLoader

with psycopg.connect("dbname=mydb") as conn:
    cursor = conn.cursor(binary=True)
    NumpyLoader.install(cursor)

    query = """
    COPY (
        SELECT array_agg(x)
        FROM generate_series(1, 100000) x
    ) TO STDOUT WITH BINARY
    """

    with cursor.copy(query) as copy:
        copy.set_types(["integer[]"])

        for row in copy.rows():
            print(row)  # numpy.ndarray
```

## ASCII STL I/O

Read and write ASCII STL files at C speed. This module is used internally
by [numpy-stl](https://github.com/WoLpH/numpy-stl) — if you want to read
or write STL files, use numpy-stl for a full-featured API. The Cython
implementation uses direct `sscanf`/`fprintf` calls, avoiding Python string
overhead entirely.

```python
from speedups._stl import ascii_read, ascii_write

# Read
with open("model.stl", "rb") as f:
    buf = f.read(8192)
    name, mesh = ascii_read(f, buf)

# Write
with open("output.stl", "wb") as f:
    ascii_write(f, b"my_model", mesh)
```

## Supported Types

| PostgreSQL | NumPy | Dimensions |
|-----------|-------|------------|
| `float4` | `float32` | 1D – ND |
| `float8` | `float64` | 1D – ND |
| `smallint` | `int16` | 1D – ND |
| `integer` | `int32` | 1D – ND |
| `bigint` | `int64` | 1D – ND |

## Compatibility

- Python 3.10, 3.11, 3.12, 3.13, 3.14
- NumPy 1.x and 2.x

## License

BSD-3-Clause
