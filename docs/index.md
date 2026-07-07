# Speedups Documentation

`speedups` contains C and Cython extensions for narrow performance-critical
paths:

- ASCII STL parsing and writing used by `numpy-stl`.
- psycopg 3 binary PostgreSQL array loading into NumPy arrays.

The README is the short package landing page. These docs cover the working
details, API contracts, and maintainer commands.

## Guides

- [PostgreSQL arrays to NumPy](postgresql.md)
- [ASCII STL I/O](stl.md)
- [Development](development.md)

## Scope

This package is intentionally small. It does not provide a general PostgreSQL
client, a high-level STL mesh API, or a documentation website. It exposes fast
building blocks for projects that already know when those low-level paths are
the right tool.
