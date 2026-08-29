# PostgreSQL Arrays to NumPy

Psycopg normally creates Python values while it decodes a PostgreSQL array.
That intermediate work adds up when the result is going straight into NumPy.
`speedups.psycopg_loaders.NumpyLoader` replaces the supported binary array
loaders and fills a `numpy.ndarray` directly.

Use it when all of these are true:

- You read PostgreSQL array values through psycopg 3.
- The query returns psycopg's binary format, usually through binary `COPY`.
- The element type is one of the supported numeric types.
- You process the result with NumPy.

## Installation

Install the PostgreSQL extra:

```bash
pip install "speedups[postgres]"
```

> [!TIP]
> Keep the quotes in zsh. Without them, the shell can interpret the square
> brackets as a glob before pip sees the package extra.

## Complete COPY Example

This COPY path needs `COPY ... WITH BINARY`. You must also call
`copy.set_types()` before reading rows. That call tells psycopg which binary
loader belongs to each column:

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

with psycopg.connect('dbname=mydb') as conn:
    cursor = conn.cursor()
    NumpyLoader.install(cursor)

    with cursor.copy(query) as copy:
        copy.set_types(['integer[]', 'float8[]'])

        for integers, floats in copy.rows():
            print(integers.dtype, integers.shape, integers.sum())
            print(floats.dtype, floats.shape, floats.mean())
```

The example prints:

```text
int32 (100000,) 5000050000
float64 (100000,) 5000.05
```

The dtypes come from the PostgreSQL element types passed to `set_types()`. The
shape shows that each `array_agg()` result contains 100,000 elements. Columns
outside the supported table keep using psycopg's registered loaders.

## Supported Types

| PostgreSQL type | NumPy dtype | Dimensions |
|:----------------|:------------|:-----------|
| `float4[]` | `float32` | 1D to ND |
| `float8[]` | `float64` | 1D to ND |
| `smallint[]` / `int2[]` | `int16` | 1D to ND |
| `integer[]` / `int4[]` | `int32` | 1D to ND |
| `bigint[]` / `int8[]` | `int64` | 1D to ND |

`NumpyLoader.install(cursor)` changes only that cursor's adapter map. It
registers the array OID for every supported type. Installation raises
`KeyError` when the connection cannot resolve one of those OIDs.

## Shapes and Empty Arrays

PostgreSQL stores array dimensions in its binary header. The loader uses that
header to preserve the shape:

```sql
SELECT '{{1, 2}, {3, 4}}'::integer[][]
```

The query decodes as an `int32` NumPy array with shape `(2, 2)`. Two dimensions
in PostgreSQL therefore remain two dimensions in NumPy.

Empty supported arrays keep their dtype and use shape `(0,)`:

```sql
SELECT '{}'::int4[], '{}'::float8[]
```

These values decode to `int32` and `float64` arrays with no elements.

## NULL Values

NULL handling depends on whether the NumPy dtype can represent a missing value:

- Float arrays decode NULL elements as `NaN`.
- Integer arrays raise `ValueError` because integer NumPy dtypes cannot
  represent PostgreSQL NULL values.

If you need nullable integer arrays, I would keep psycopg's regular Python-list
loader and choose the missing-value representation after decoding. Converting
the data to a floating-point array with `NaN` in SQL is also valid when that
change matches the application.

## Lower Bounds

PostgreSQL arrays can start at a lower bound other than 1. NumPy has no matching
lower-bound concept, so this loader accepts only a lower bound of 1. Any other
lower bound raises `ValueError` instead of silently shifting the indexes.

## Troubleshooting

### Rows contain Python lists

For a regular `SELECT`, create a binary cursor so psycopg selects binary
loaders. A binary COPY gets its format from `COPY ... WITH BINARY`, so the
cursor itself does not need `binary=True`. In both cases, install the loader on
the cursor that reads the result:

```python
cursor = conn.cursor()
NumpyLoader.install(cursor)

with cursor.copy(binary_copy_query) as copy:
    copy.set_types(['integer[]'])
```

The brackets in `'integer[]'` matter. Passing `'integer'` selects the scalar
loader, which does not produce a NumPy array.

### `KeyError: Adapter type not found`

The connection could not resolve one of the supported PostgreSQL array OIDs.
Check the connection before calling `NumpyLoader.install()` and confirm that
psycopg loaded the built-in PostgreSQL type metadata.

### Unsupported array type

Only the numeric array types listed above use the optimized loader. Keep
psycopg's regular loaders for text, boolean, JSON, UUID, and user-defined
arrays.
