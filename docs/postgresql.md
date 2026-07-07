# PostgreSQL Arrays to NumPy

`speedups.psycopg_loaders.NumpyLoader` registers psycopg 3 binary array loaders
that decode supported PostgreSQL numeric arrays directly into `numpy.ndarray`
values.

Use it when all of these are true:

- You are reading PostgreSQL array values through psycopg 3.
- The data uses psycopg's binary format, especially binary `COPY`.
- The element type is one of the supported numeric types.
- The result will be processed with NumPy.

## Installation

Install the PostgreSQL extra:

```bash
pip install "speedups[postgres]"
```

The quotes are useful in shells such as zsh, where unquoted square brackets can
be interpreted as glob syntax.

## Complete COPY Example

The optimized path depends on a binary cursor and a binary `COPY` stream. Call
`copy.set_types()` before reading rows so psycopg knows which loaders to use for
the binary columns.

```python
import psycopg

from speedups.psycopg_loaders import NumpyLoader

query = """
COPY (
    SELECT
        array_agg(x::integer),
        array_agg((x::double precision) / 10)
    FROM generate_series(1, 100000) AS series(x)
) TO STDOUT WITH BINARY
"""

with psycopg.connect("dbname=mydb") as conn:
    cursor = conn.cursor(binary=True)
    NumpyLoader.install(cursor)

    with cursor.copy(query) as copy:
        copy.set_types(["integer[]", "float8[]"])

        for integers, floats in copy.rows():
            print(integers.dtype, integers.shape, integers.sum())
            print(floats.dtype, floats.shape, floats.mean())
```

The rows yielded by `copy.rows()` contain NumPy arrays for supported numeric
arrays. Other column types continue to use the loaders registered by psycopg.

## Supported Types

| PostgreSQL type | NumPy dtype | Dimensions |
|:----------------|:------------|:-----------|
| `float4[]` | `float32` | 1D to ND |
| `float8[]` | `float64` | 1D to ND |
| `smallint[]` / `int2[]` | `int16` | 1D to ND |
| `integer[]` / `int4[]` | `int32` | 1D to ND |
| `bigint[]` / `int8[]` | `int64` | 1D to ND |

`NumpyLoader.install(cursor)` registers loaders for the supported array OIDs on
that cursor's adapter map. If psycopg cannot resolve one of the required array
types on the connection, installation raises `KeyError`.

## Shapes and Empty Arrays

PostgreSQL array dimensions are preserved:

```sql
SELECT '{{1, 2}, {3, 4}}'::integer[][]
```

decodes as an `int32` NumPy array with shape `(2, 2)`.

Empty supported arrays keep their dtype and use shape `(0,)`:

```sql
SELECT '{}'::int4[], '{}'::float8[]
```

decodes to `int32` and `float64` arrays with no elements.

## NULL Values

NULL handling depends on the target dtype:

- Float arrays decode NULL elements as `NaN`.
- Integer arrays raise `ValueError` because integer NumPy dtypes cannot
  represent PostgreSQL NULL values.

If you need nullable integer arrays, convert them in SQL before COPY, choose a
float representation with `NaN`, or use psycopg's regular Python-list loaders.

## Lower Bounds

PostgreSQL arrays can have non-default lower bounds. This loader supports only
arrays whose lower bound is 1. Arrays with another lower bound raise
`ValueError`.

## Troubleshooting

### Rows contain Python lists

Check that the cursor is binary and that `copy.set_types()` uses array types:

```python
cursor = conn.cursor(binary=True)
NumpyLoader.install(cursor)

with cursor.copy(query) as copy:
    copy.set_types(["integer[]"])
```

### `KeyError: Adapter type not found`

The connection could not find one of the supported PostgreSQL array types while
installing the loader. Check that the connection is usable and that psycopg has
loaded the built-in PostgreSQL type metadata.

### Unsupported array type

Only the numeric array types listed above use the optimized loader. Text,
boolean, JSON, UUID, and user-defined arrays should use psycopg's regular
loaders unless support is added explicitly.
