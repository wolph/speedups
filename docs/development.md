# Development

This package builds Cython extensions and ships typed Python modules. Keep
`setup.py`; it is required for extension compilation.

## Setup

Install all extras with uv:

```bash
uv sync --all-extras
```

## Focused Tests

The STL tests do not need external services:

```bash
uv run pytest tests/test_stl.py
```

The low-level PostgreSQL binary array converter tests also run without a
PostgreSQL server:

```bash
uv run pytest tests/test_psycopg_array.py
```

The psycopg loader integration tests need PostgreSQL and `pg_config`.

Start a local PostgreSQL container:

```bash
docker run -d --name test-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

Then run:

```bash
uv run pytest tests/test_arrays.py
```

## Lint and Type Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run codespell .
uv run pyright speedups tests
uv run mypy speedups
```

Configuration lives in `ruff.toml` and `pyproject.toml`.

## Full Quality Gate

Run the full tox matrix before publishing changes:

```bash
uvx --with tox-uv tox -p auto
```

All environments should pass.

## Cython Notes

- Every `.pyx` module should have a matching `.pyi` stub.
- `speedups/stl.pyx` intentionally uses `language_level=2`.
- `speedups/psycopg_array.pyx` uses `language_level=3`.
- Cython modules are tested through integration behavior, not Python coverage
  instrumentation.

## Benchmarks

Benchmark code lives in `benchmarks/run_benchmarks.py`; generated charts live
in `benchmarks/results/`. Do not change benchmark numbers in docs unless the
benchmark suite was intentionally rerun and the generated results were updated.
