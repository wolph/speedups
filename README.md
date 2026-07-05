# Speedups

[![CI](https://github.com/wolph/speedups/actions/workflows/ci.yml/badge.svg)](https://github.com/wolph/speedups/actions/workflows/ci.yml)
[![Build Wheels](https://github.com/wolph/speedups/actions/workflows/build_wheels.yml/badge.svg)](https://github.com/wolph/speedups/actions/workflows/build_wheels.yml)
[![PyPI](https://img.shields.io/pypi/v/speedups.svg)](https://pypi.org/project/speedups/)
[![Python](https://img.shields.io/pypi/pyversions/speedups.svg)](https://pypi.org/project/speedups/)
[![License](https://img.shields.io/pypi/l/speedups.svg)](https://github.com/WoLpH/speedups/blob/master/LICENSE)

`speedups` provides C and Cython extensions for fast ASCII STL I/O and
PostgreSQL binary array to NumPy conversion. It is a small package for
performance-critical paths where avoiding Python object allocation matters.

The package currently covers two workloads:

- Fast ASCII STL parsing and writing, used by
  [numpy-stl](https://github.com/WoLpH/numpy-stl).
- Fast psycopg 3 binary PostgreSQL array loading into `numpy.ndarray` values.

## Installation

Install the core package:

```bash
pip install speedups
```

Install with PostgreSQL loader support:

```bash
pip install "speedups[postgres]"
```

The quoted extra form works in shells such as zsh that otherwise treat square
brackets as glob syntax.

## Quick Start

Use `NumpyLoader` when reading supported PostgreSQL arrays through psycopg's
binary protocol:

```python
import psycopg

from speedups.psycopg_loaders import NumpyLoader

query = """
COPY (
    SELECT array_agg(x)
    FROM generate_series(1, 100000) AS series(x)
) TO STDOUT WITH BINARY
"""

with psycopg.connect("dbname=mydb") as conn:
    cursor = conn.cursor(binary=True)
    NumpyLoader.install(cursor)

    with cursor.copy(query) as copy:
        copy.set_types(["integer[]"])
        for row in copy.rows():
            values = row[0]
            print(values.dtype, values.shape, values.sum())
```

Use the STL helpers only when you already have data in the low-level
`numpy-stl` mesh dtype:

```python
from speedups.stl import ascii_read, ascii_write

with open("model.stl", "rb") as fh:
    buffer = fh.read(8192)
    name, mesh = ascii_read(fh, buffer)

with open("copy.stl", "wb") as fh:
    ascii_write(fh, name.strip() or b"model", mesh)
```

## PostgreSQL Array to NumPy

`speedups.psycopg_loaders.NumpyLoader` registers optimized psycopg binary array
loaders for supported numeric PostgreSQL array types. For those arrays, psycopg
returns `numpy.ndarray` objects instead of Python lists.

The optimized path is useful when reading large arrays through binary `COPY`,
for example bulk analytical data that will immediately be processed with NumPy.

```python
import psycopg

from speedups.psycopg_loaders import NumpyLoader

query = """
COPY (
    SELECT
        '{0.1, 0.2}'::float4[],
        '{1, 2, 3}'::integer[],
        '{{1, 2}, {3, 4}}'::bigint[][]
) TO STDOUT WITH BINARY
"""

with psycopg.connect("dbname=mydb") as conn:
    cursor = conn.cursor(binary=True)
    NumpyLoader.install(cursor)

    with cursor.copy(query) as copy:
        copy.set_types(["float4[]", "integer[]", "bigint[]"])

        for floats, integers, matrix in copy.rows():
            print(floats.dtype, floats.shape)
            print(integers.dtype, integers.shape)
            print(matrix.dtype, matrix.shape)
```

Important details:

- Use a binary cursor and binary `COPY` for the optimized COPY workflow.
- Call `copy.set_types([...])` before reading from `copy.rows()`.
- `NumpyLoader.install(cursor)` registers only the supported numeric array OIDs.
- Unsupported array types continue to use psycopg's regular loaders.
- Multi-dimensional arrays are supported.
- PostgreSQL array lower bounds must be 1.
- Empty supported arrays keep their dtype and have shape `(0,)`.
- Float NULL elements decode as `NaN`.
- Integer NULL elements raise `ValueError`.

## ASCII STL I/O

`speedups.stl` provides low-level ASCII STL parsing and writing at C speed. The
module is used internally by [numpy-stl](https://github.com/WoLpH/numpy-stl).

Most users should use `numpy-stl` for full STL file handling. Use this module
directly only when you already work with the low-level structured NumPy mesh
array expected by `numpy-stl`.

```python
from speedups.stl import ascii_read

with open("model.stl", "rb") as fh:
    buffer = fh.read(8192)
    name, mesh = ascii_read(fh, buffer)

print(name.strip())
print(mesh.dtype)
print(mesh["vectors"].shape)
```

`ascii_read()` expects the file handle to be positioned immediately after the
initial buffer read. It returns the solid name as `bytes` and a structured NumPy
array of facets.

```python
import numpy as np

from speedups.stl import ascii_write

mesh_dtype = np.dtype(
    [
        ("normals", np.float32, 3),
        ("vectors", np.float32, (3, 3)),
        ("attr", np.uint16, (1,)),
    ]
)

mesh = np.zeros(1, dtype=mesh_dtype)
mesh["normals"][0] = [0.0, 0.0, 1.0]
mesh["vectors"][0] = [
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
]

with open("triangle.stl", "wb") as fh:
    ascii_write(fh, b"triangle", mesh)
```

Malformed ASCII STL input raises parser errors such as `RuntimeError`. Overlong
lines are rejected instead of being truncated.

## Supported PostgreSQL Array Types

| PostgreSQL type | NumPy dtype | Dimensions |
|:----------------|:------------|:-----------|
| `float4[]` | `float32` | 1D to ND |
| `float8[]` | `float64` | 1D to ND |
| `smallint[]` / `int2[]` | `int16` | 1D to ND |
| `integer[]` / `int4[]` | `int32` | 1D to ND |
| `bigint[]` / `int8[]` | `int64` | 1D to ND |

## Performance

The benchmark charts below show the intended performance profile: the Cython
paths avoid Python object overhead and are substantially faster for the covered
workloads. Exact timings depend on CPU, compiler, Python, NumPy, and
PostgreSQL versions, so treat the numbers as measured examples rather than a
guaranteed speedup on every machine.

<p align="center">
  <img src="https://raw.githubusercontent.com/wolph/speedups/develop/benchmarks/results/stl_performance.svg" alt="STL I/O Performance" width="700">
</p>

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

<p align="center">
  <img src="https://raw.githubusercontent.com/wolph/speedups/develop/benchmarks/results/pg_array_performance.svg" alt="PostgreSQL COPY to NumPy Performance" width="700">
</p>

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

<sub>Benchmarked on Apple M2 Pro, Python 3.14, macOS 15.4. PostgreSQL data was
pre-populated in tables to isolate COPY and conversion time. Array dimensionality
(1D, 2D, 3D) has no significant effect on performance.</sub>

## Compatibility

- Python 3.10, 3.11, 3.12, 3.13, and 3.14
- NumPy 1.x and 2.x
- psycopg 3.0.8 or newer for PostgreSQL support

## Development

Install all development dependencies:

```bash
uv sync --all-extras
```

Run focused tests:

```bash
uv run pytest tests/test_stl.py
uv run pytest tests/test_psycopg_array.py
```

`tests/test_arrays.py` requires PostgreSQL. A quick local PostgreSQL instance:

```bash
docker run -d --name test-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

Then run:

```bash
uv run pytest tests/test_arrays.py
```

Run lint and type checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run codespell .
uv run pyright speedups tests
uv run mypy speedups
```

Run the full quality gate:

```bash
uvx --with tox-uv tox -p auto
```

`setup.py` is required for Cython extension compilation and should stay in the
project.

## License

BSD-3-Clause
