# Speedups

C/Cython extension library: fast ASCII STL I/O and PostgreSQL binary
array to NumPy conversion. Python >=3.10, BSD-3-Clause.

## Build

```sh
uv sync --all-extras
```

`setup.py` is required for Cython extension compilation -- do not remove
or replace it.

## Test

```sh
uv run pytest tests/test_stl.py       # no external deps
uv run pytest tests/test_arrays.py    # requires running PostgreSQL
```

Quick PG setup:

```sh
docker run -d --name test-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

## Lint & Typecheck

```sh
uv run ruff check . && uv run ruff format --check . && uv run codespell .
uv run pyright speedups tests && uv run mypy speedups
```

Config lives in `ruff.toml` and `pyproject.toml`.

## Quality Gate

Before reporting work as complete, run the full tox suite and confirm
it passes:

```sh
uvx --with tox-uv tox run -p<number-of-cpu-cores>
```

All environments must pass. Do not present results to the user until
tox is green -- fix issues yourself first.

Do not modify existing tests to make them pass. The existing tests are
correct and verify backwards compatibility. If a test fails, fix your
code, not the test.

## Gotchas

- `_stl.pyx` uses `language_level=2` intentionally (C string ops,
  `sscanf`/`fprintf`) -- do not "upgrade" it to 3
- `psycopg_array.pyx` uses `language_level=3`
- Every `.pyx` module must have a corresponding `.pyi` type stub
- Type hints required on all new/modified `.py` files (except
  `__init__.py`, `__about__.py`)
- Use `from __future__ import annotations` in type-checked pure Python
  modules
- Dual-checker type ignore syntax:
  `# type: ignore[mypy-code, ty:ty-code]`
- Cython modules cannot be measured by Python coverage tools -- test
  indirectly via integration tests
- `hton.h` is vendored from MagicStack/py-pgproto (Apache 2.0) --
  update from upstream, don't modify in-place
