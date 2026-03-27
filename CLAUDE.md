# CLAUDE.md -- Speedups Project

## Project Overview

Speedups is a Python library providing C and Cython extensions
for speeding up common operations. It is externalized so that dependent
projects avoid the hassle of building binary wheels themselves.

Two main features:

- **STL ASCII I/O** (`speedups._stl`) -- Fast Cython-based ASCII STL file
  reader and writer using C `FILE*` operations. Exposes `ascii_read()` and
  `ascii_write()` functions for reading/writing STL mesh data as NumPy
  structured arrays (normals, vectors, attributes).

- **PostgreSQL binary array to NumPy conversion**
  (`speedups.psycopg_array` / `speedups.psycopg_loaders`) -- Converts
  PostgreSQL binary `COPY` array data directly into NumPy ndarrays via
  Cython, avoiding slow element-by-element Python unpacking. Supports
  float4, float8, smallint, integer, and bigint types in 1D through N-D.

Authors: Rick van Hattem, Joren Hammudoglu
License: BSD-3-Clause
Repository: https://github.com/WoLpH/speedups/
Python: >=3.10

## Architecture

```
speedups/
  __init__.py            # Public API: exports ascii_read, ascii_write
  __about__.py           # Package metadata (__version__, __author__, etc.)
  _stl.pyx               # Cython (language_level=2): ASCII STL I/O
  _stl.pyi               # Type stub for _stl Cython module
  psycopg_array.pyx      # Cython (language_level=3): binary array -> numpy
  psycopg_array.pyi      # Type stub for psycopg_array Cython module
  psycopg_loaders.py     # Pure Python: NumpyLoader for psycopg COPY
  hton.h                 # C header: platform-agnostic endian conversion
  hton.pxd               # Cython declaration file for hton.h
  py.typed               # PEP 561 marker for typed package
setup.py                 # Cython extension build (numpy.get_include())
pyproject.toml           # Project metadata, build-system, tool config
tests/
  test_speedups.py       # STL ASCII I/O tests (no external deps)
  test_arrays.py         # PostgreSQL array tests (requires psycopg + PG)
```

### Key modules

- `_stl.pyx` -- Cython (language_level=2) ASCII STL reader/writer.
  See Cython Notes for implementation details.
- `psycopg_array.pyx` -- Cython (language_level=3) binary array to
  numpy converter. See Cython Notes for implementation details.
- `psycopg_loaders.py` -- Pure Python `NumpyLoader` class (psycopg
  `ArrayBinaryLoader` subclass) that parses PostgreSQL binary array
  headers and delegates to the Cython converter functions.
- `hton.h` / `hton.pxd` -- Platform-agnostic endian conversion
  (sourced from MagicStack/py-pgproto). See Cython Notes.

## Build & Development

### Installation

```bash
uv sync --all-groups
```

This installs the package in development mode with all dependency groups
(dev, test, lint, typecheck). Cython extensions are compiled automatically
via the setuptools build backend during `uv sync`.

### Why setup.py is kept

`setup.py` is required for Cython extension building. It calls
`cythonize()` on `.pyx` files and creates extensions with
`numpy.get_include()`, `NPY_NO_DEPRECATED_API` macro, and the
`speedups/` directory in include paths (for `hton.h`). Default
`CFLAGS=-O3`. The build-system in `pyproject.toml` specifies setuptools
as the backend with Cython and NumPy as build-time requirements.

### Dependency groups

| Group     | Contents                                    |
|-----------|---------------------------------------------|
| dev       | Includes test + lint + typecheck groups      |
| test      | pytest, pytest-postgresql, psycopg[binary]   |
| lint      | ruff, codespell                              |
| typecheck | pyright, mypy                                |

### Optional dependencies

- `speedups[postgres]` -- Adds psycopg>=3.0.8 for PostgreSQL support.

## Testing

### STL tests (no external dependencies)

```bash
uv run pytest tests/test_speedups.py
```

Tests ASCII STL read, write, and roundtrip using temporary files.

### PostgreSQL tests (requires running PostgreSQL)

```bash
uv run pytest tests/test_arrays.py
```

Requires a running PostgreSQL instance. Uses `pytest-postgresql` fixtures.
Tests 1D/2D array loading, type casting, and `NumpyLoader.install()`
integration with psycopg binary COPY.

### Quick PostgreSQL setup with Docker

```bash
docker run -d --name test-pg \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16
```

### Run all tests

```bash
uv run pytest
```

## Code Quality

### Linting

```bash
uv run ruff check .
uv run ruff format --check .
uv run codespell .
```

### Type checking

```bash
uv run pyright speedups tests
uv run mypy speedups
```

Pyright: standard mode, strict for `speedups/`. Mypy: checks `speedups/`
and `tests/` with `warn_return_any`, `check_untyped_defs` enabled.

### Experimental type checkers

```bash
uvx ty check speedups
uvx pyrefly check speedups
```

These run as `continue-on-error` in CI -- not required to pass.

## Code Conventions

### Formatting

- 79-character line length (configured in `[tool.ruff]`)
- Single quotes for strings (`quote-style = 'single'`)
- 4-space indentation
- Target Python version: 3.10

### Naming

- `snake_case` for functions, variables, and module names
- `PascalCase` for classes (e.g., `NumpyLoader`, `Facet`)
- `UPPER_CASE` for constants (e.g., `ALLOC_SIZE`, `BUF_SIZE`)
- Private/internal names prefixed with underscore (e.g., `_stl`, `_struct_head`)

### Type hints

- Type hints required for all Python code
- `.pyi` stub files provided for Cython modules (`_stl.pyi`,
  `psycopg_array.pyi`)
- `py.typed` marker present for PEP 561 compliance
- `from __future__ import annotations` used in pure Python modules

### Dual-checker type ignore pattern

When both mypy and ty (or other checkers) need ignores on the same line:

```python
# type: ignore[mypy-code, ty:ty-code]
```

### Import style

- `isort` via ruff with `known-first-party = ['speedups']`
- Standard library, third-party, then first-party grouping
- `TYPE_CHECKING` blocks for import-only type dependencies

### Mypy/pyright overrides for Cython

Cython extensions cannot be analyzed directly by type checkers. Mypy uses
`ignore_missing_imports = true`; pyright uses the `.pyi` stub files. See
Special Patterns for the full config.

## CI/CD

### GitHub Actions workflows

**ci.yml** (triggered on push):

- **Lint job** -- Runs `ruff check`, `ruff format --check`, and `codespell`
- **Typecheck job** -- Runs `pyright`, `mypy`, `ty` (experimental),
  `pyrefly` (experimental)
- **Test job** -- Matrix across Python 3.10, 3.11, 3.12, 3.13, 3.14.
  Uses `uv sync --group test` and `uv run pytest`. Builds with
  `CFLAGS='-O0 -g'` for debug symbols.

**build_wheels.yml** (triggered on push, pull_request, workflow_dispatch):

- **Fast wheel build** -- develop branch pushes build cp313-manylinux_x86_64
- **Full wheel build** -- Version tag pushes (`refs/tags/v*`) build on
  ubuntu/windows/macos via cibuildwheel (skips PyPy, Python <3.10, win32,
  i686). Linux: x86_64 + aarch64.
- **SDist + PyPI publish** -- Builds sdist and publishes all artifacts to
  PyPI using trusted publishing (`pypa/gh-action-pypi-publish`)

## Cython Notes

### _stl.pyx (language_level=2)

- Uses `language_level=2` because it relies on C-style string operations
  and `sscanf`/`fprintf` for STL format parsing.
- Defines a packed C struct `Facet` matching the NumPy dtype.
- Uses `FILE*` from `libc.stdio` with `fdopen(dup(fh.fileno()))` to get a
  C file handle from a Python file object.
- Implements buffered line reading (`readline`) with an 8KB buffer.
- On Linux, temporarily switches locale to "C" via `uselocale()` for
  consistent floating-point parsing.
- Pre-allocates arrays in chunks of 200,000 facets, resizing as needed.

### psycopg_array.pyx (language_level=3)

- Uses Cython fused types (`int_output_type`, `float_output_type`) for
  generic handling of int16/int32/int64 and float/double.
- Runs conversion loops with `nogil` for performance.
- Calls `hton.unpack_*` functions for network-to-host byte order
  conversion of each array element.
- Handles NULL values: floats become NaN, integers raise `ValueError`.
- Uses `@cython.boundscheck(False)` and `@cython.wraparound(False)` for
  maximum performance.

### hton.h -- endian conversion

- Sourced from MagicStack/py-pgproto (Apache 2.0).
- Detects platform byte order at compile time.
- Uses compiler builtins (`__builtin_bswap*` for GCC/Clang,
  `_byteswap_*` for MSVC) when available.
- Falls back to manual bit-shifting implementations.
- Provides `pack_*` (host-to-network) and `unpack_*` (network-to-host)
  for int16, int32, int64, float, and double.

### Extension build (setup.py)

The `cythonize()` call sets `language_level=3` as a default, but
`_stl.pyx` overrides this with its `# cython: language_level=2` directive.
See Build & Development for the full setup.py details.

## Special Patterns

### PostgreSQL test fixtures

Tests in `test_arrays.py` use `pytest-postgresql` which provides a
`postgresql` fixture that manages a temporary PostgreSQL instance. The
fixture is function-scoped and provides a `psycopg.Connection`.

### Cython coverage limitations

Cython modules (`_stl`, `psycopg_array`) cannot be measured by standard
Python coverage tools. Test coverage for these modules is verified
indirectly through integration tests that exercise the Python-facing APIs.

### Type checker overrides for Cython imports

Mypy config in `pyproject.toml` includes overrides to suppress missing
import errors for Cython extension modules:

```toml
[[tool.mypy.overrides]]
module = ['speedups._stl', 'speedups.psycopg_array']
ignore_missing_imports = true
```

Pyright relies on the `.pyi` stub files to understand the Cython modules'
type signatures without importing them.

### NumpyLoader registration pattern

`NumpyLoader.install(cursor)` registers the loader for all supported
PostgreSQL array types on a given cursor. Must be called per-cursor
before executing COPY queries.

### STL test fixtures from numpy-stl

`test_speedups.py` optionally loads ASCII STL files from a sibling
`numpy-stl/tests/stl_ascii/` directory (skipped if not found).

### Version management

Version is defined in `speedups/__about__.py` and read dynamically by
setuptools via `[tool.setuptools.dynamic] version = {attr = ...}`.
