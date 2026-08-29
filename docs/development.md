# Development

This package compiles Cython extensions while it builds. Keep `setup.py`
because the build backend calls it to compile those extensions.

## Setup

Install the package and every development dependency with uv:

```bash
uv sync --all-extras
```

## Focused tests

The STL tests do not need external services:

```bash
uv run pytest tests/test_stl.py
```

The low-level PostgreSQL binary array converter tests also run without a
PostgreSQL server:

```bash
uv run pytest tests/test_psycopg_array.py
```

The psycopg loader integration tests use the `pytest-postgresql` `postgresql`
fixture. The fixture finds `pg_ctl` through `pg_config` and starts a temporary
local server. Check the resolved binary directory before running the
integration tests:

```bash
command -v pg_config
pg_config --bindir
```

> [!NOTE]
> A PostgreSQL Docker container on port 5432 does not satisfy the current
> fixture. The tests request the process-backed `postgresql` fixture rather
> than `postgresql_noproc`.

Once the local PostgreSQL executables are available, run:

```bash
uv run pytest tests/test_arrays.py
```

## Lint and type checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run codespell .
uv run pyright speedups tests
uv run mypy speedups
```

Ruff and codespell check the source and documentation. Pyright and mypy check
the typed Python API. Their configuration lives in `ruff.toml` and
`pyproject.toml`.

## Full quality gate

Run the full tox matrix before you publish changes:

```bash
uvx --with tox-uv tox -p auto
```

Tox builds the extension against every supported Python and NumPy combination,
then runs the lint and type-check environments. A successful run ends with
every environment marked `OK`.

## Cython notes

- Every `.pyx` module should have a matching `.pyi` stub.
- `speedups/stl.pyx` intentionally uses `language_level=2`.
- `speedups/psycopg_array.pyx` uses `language_level=3`.
- Python coverage cannot measure lines inside compiled Cython modules. Test
  their behavior through the Python API instead.

## Benchmarks

Benchmark code lives in `benchmarks/run_benchmarks.py`. Generated charts live
in `benchmarks/results/`. Change benchmark numbers in the documentation only
when you intentionally rerun the suite and update its generated results.
