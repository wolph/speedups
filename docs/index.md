# Speedups documentation

`speedups` handles two narrow paths where creating Python objects adds
measurable overhead:

- Parse and write ASCII STL data for `numpy-stl`.
- Load psycopg 3 binary PostgreSQL arrays directly into NumPy arrays.

The README gets you to the first working call. These guides cover the API
contracts, failure modes, and maintainer commands you need after that.

## Guides

```{toctree}
:maxdepth: 2

postgresql
stl
development
```

## Scope

This package is intentionally small. It is not a PostgreSQL client or a
high-level STL mesh API. Use it when your project already owns those layers and
needs a faster conversion step underneath them.
