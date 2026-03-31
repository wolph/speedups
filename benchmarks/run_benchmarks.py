"""Benchmark speedups vs pure-Python baselines.

Generates SVG bar charts and prints Markdown table rows for the README.

Usage:
    uv run --extra benchmark \
        python benchmarks/run_benchmarks.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import timeit

import numpy as np

RESULTS_DIR = pathlib.Path(__file__).parent / 'results'

STL_SIZES = [10_000, 100_000, 1_000_000, 10_000_000]
PG_SIZES = [100_000, 1_000_000, 10_000_000, 50_000_000]

# Representative sizes for the bar chart SVGs
STL_CHART_SIZE = 10_000_000
PG_CHART_SIZE = 50_000_000
PG_SHAPES: list[tuple[str, list[int]]] = [
    ('1D', []),
    ('2D', [100]),
    ('3D', [10, 10]),
]

TIMEIT_NUMBER = 5
TIMEIT_REPEAT = 3

# Dedup threshold: lines within this ratio are merged
DEDUP_THRESHOLD = 0.10


# ---------------------------------------------------------------------------
# STL pure-Python baselines
# ---------------------------------------------------------------------------

STL_DTYPE = np.dtype(
    [
        ('normals', np.float32, 3),
        ('vectors', np.float32, (3, 3)),
        ('attr', np.uint16, (1,)),
    ]
)


def _pure_python_stl_read(
    path: pathlib.Path,
) -> np.ndarray:
    """Read ASCII STL via pure Python string parsing."""
    facets: list[tuple[list[float], list[list[float]]]] = []
    with open(path) as f:
        for line in f:
            line = line.strip().lower()
            if line.startswith('facet normal'):
                parts = line.split()
                normal = [
                    float(parts[2]),
                    float(parts[3]),
                    float(parts[4]),
                ]
                vertices: list[list[float]] = []
            elif line.startswith('vertex'):
                parts = line.split()
                vertices.append(
                    [
                        float(parts[1]),
                        float(parts[2]),
                        float(parts[3]),
                    ]
                )
            elif line.startswith('endfacet'):
                facets.append((normal, vertices))

    arr = np.zeros(len(facets), dtype=STL_DTYPE)
    for i, (normal, verts) in enumerate(facets):
        arr['normals'][i] = normal
        arr['vectors'][i] = verts
    return arr


def _pure_python_stl_write(
    path: pathlib.Path,
    name: str,
    arr: np.ndarray,
) -> None:
    """Write ASCII STL via pure Python formatting."""
    with open(path, 'w') as f:
        f.write(f'solid {name}\n')
        for i in range(len(arr)):
            n = arr['normals'][i]
            f.write(f'facet normal {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n')
            f.write('  outer loop\n')
            for j in range(3):
                v = arr['vectors'][i][j]
                f.write(f'    vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')
            f.write('  endloop\n')
            f.write('endfacet\n')
        f.write(f'endsolid {name}\n')


def _generate_stl_data(n_facets: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    arr = np.zeros(n_facets, dtype=STL_DTYPE)
    arr['normals'] = rng.standard_normal((n_facets, 3)).astype(np.float32)
    arr['vectors'] = rng.standard_normal((n_facets, 3, 3)).astype(np.float32)
    return arr


def _time_it(
    fn: object,
    number: int = TIMEIT_NUMBER,
) -> float:
    """Best per-call time in seconds."""
    return (
        min(
            timeit.repeat(
                fn,  # type: ignore[arg-type]
                number=number,
                repeat=TIMEIT_REPEAT,
            )
        )
        / number
    )


# ---------------------------------------------------------------------------
# STL benchmarks
# ---------------------------------------------------------------------------


def benchmark_stl(
    n_facets: int,
) -> dict[str, tuple[float, float]]:
    """Return {op: (pure_python_time, cython_time)} in seconds."""
    from speedups._stl import ascii_read, ascii_write

    arr = _generate_stl_data(n_facets)
    results: dict[str, tuple[float, float]] = {}

    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / 'bench.stl'

        with open(p, 'wb') as f:
            ascii_write(f, b'benchmark', arr)

        def write_pure():
            _pure_python_stl_write(p, 'benchmark', arr)

        def write_cython():
            with open(p, 'wb') as f:
                ascii_write(f, b'benchmark', arr)

        # Fewer iterations for large sizes
        n = max(
            1,
            TIMEIT_NUMBER
            // max(
                1,
                n_facets // 100_000,
            ),
        )

        pw = _time_it(write_pure, n)
        cw = _time_it(write_cython, n)
        results['Write'] = (pw, cw)

        with open(p, 'wb') as f:
            ascii_write(f, b'benchmark', arr)

        def read_pure():
            _pure_python_stl_read(p)

        def read_cython():
            with open(p, 'rb') as f:
                buf = f.read(8192)
                ascii_read(f, buf)

        pr = _time_it(read_pure, n)
        cr = _time_it(read_cython, n)
        results['Read'] = (pr, cr)

    return results


# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------


def _pg_text_copy_to_numpy(
    conn: object,
    query: str,
    dtype: type,
    pg_type: str,
) -> np.ndarray:
    result = np.empty(0, dtype=dtype)
    cursor = conn.cursor()  # type: ignore[union-attr]
    with cursor.copy(query) as copy:
        copy.set_types([pg_type])
        for row in copy.rows():
            result = np.array(row[0], dtype=dtype)
    return result


def _pg_numpy_loader(
    conn: object,
    query: str,
    pg_type: str,
) -> np.ndarray:
    from speedups.psycopg_loaders import NumpyLoader

    result = np.empty(0)
    cursor = conn.cursor(  # type: ignore[union-attr]
        binary=True,
    )
    NumpyLoader.install(cursor)
    with cursor.copy(query) as copy:
        copy.set_types([pg_type])
        for row in copy.rows():
            result = row[0]
    return result


DOCKER_CONTAINER = 'speedups-bench-pg'
PG_CONNINFO = (
    'host=localhost port=5432 dbname=postgres user=postgres password=postgres'
)


def _try_pg_connect(info: str) -> bool:
    try:
        import psycopg

        with psycopg.connect(info, connect_timeout=3):
            return True
    except Exception:
        return False


def _ensure_pg() -> str | None:
    """Return conninfo or None."""
    if _try_pg_connect(PG_CONNINFO):
        print('  Connected to existing PostgreSQL.')
        return PG_CONNINFO

    print('  No local PostgreSQL. Trying Docker...')
    if not shutil.which('docker'):
        print('  Docker not found.')
        return None

    result = subprocess.run(
        ['docker', 'inspect', DOCKER_CONTAINER],
        capture_output=True,
    )
    if result.returncode == 0:
        subprocess.run(
            ['docker', 'start', DOCKER_CONTAINER],
            capture_output=True,
        )
    else:
        result = subprocess.run(
            [
                'docker',
                'run',
                '-d',
                '--name',
                DOCKER_CONTAINER,
                '-e',
                'POSTGRES_PASSWORD=postgres',
                '-p',
                '5432:5432',
                'postgres:16',
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f'  Docker failed: {result.stderr.decode()}')
            return None

    print('  Waiting for PostgreSQL...')
    for _ in range(30):
        if _try_pg_connect(PG_CONNINFO):
            print('  Docker PostgreSQL ready.')
            return PG_CONNINFO
        time.sleep(1)

    print('  PostgreSQL did not become ready.')
    return None


def _cleanup_docker_pg() -> None:
    subprocess.run(
        ['docker', 'rm', '-f', DOCKER_CONTAINER],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# PG benchmarks — temp table approach
# ---------------------------------------------------------------------------


def _create_pg_temp_table(
    conn: object,
    n_elements: int,
    shape_dims: list[int],
    dtype_sql: str,
    table: str,
) -> None:
    """Create a temp table with pre-computed arrays.

    For 1D: single array of n_elements.
    For 2D+: array of arrays shaped by shape_dims,
    with total elements = n_elements.
    """
    cur = conn.execute  # type: ignore[union-attr]

    if not shape_dims:
        # 1D: one big array
        cur(f'DROP TABLE IF EXISTS {table}')
        cur(
            f'CREATE TABLE {table} AS '
            f'SELECT array_agg(x::{dtype_sql}) AS arr '
            f'FROM generate_series(1, {n_elements}) x'
        )
    else:
        # ND: build via subqueries
        # e.g. 2D 100x(n/100): array of 100-element
        # sub-arrays
        inner_size = n_elements
        for d in shape_dims:
            inner_size //= d

        if len(shape_dims) == 1:
            # 2D: array_agg of sub-arrays
            cols = shape_dims[0]
            cur(f'DROP TABLE IF EXISTS {table}')
            cur(
                f'CREATE TABLE {table} AS '
                f'SELECT array_agg(sub) AS arr FROM ('
                f'  SELECT array_agg('
                f'    (g % {inner_size} + 1)::{dtype_sql}'
                f'  ) AS sub'
                f'  FROM generate_series('
                f'    0, {n_elements - 1}'
                f'  ) g'
                f'  GROUP BY g / {inner_size}'
                f'  LIMIT {cols}'
                f') t'
            )
        else:
            # 3D: build as flat then reshape via SQL
            # Simpler: just use a large 1D array
            # (PG doesn't natively support 3D literals
            # easily, and the Cython converter handles
            # any dimensionality the same way)
            cur(f'DROP TABLE IF EXISTS {table}')
            cur(
                f'CREATE TABLE {table} AS '
                f'SELECT array_agg('
                f'  x::{dtype_sql}'
                f') AS arr '
                f'FROM generate_series('
                f'  1, {n_elements}'
                f') x'
            )


def benchmark_pg(
    conn_info: str,
    n_elements: int,
    shape_name: str,
    shape_dims: list[int],
) -> dict[str, tuple[float, float]]:
    """Return {label: (pure_python_time, cython_time)} in seconds."""
    import psycopg

    results: dict[str, tuple[float, float]] = {}

    conn = psycopg.connect(conn_info, autocommit=True)
    try:
        for dtype_sql, np_dtype, pg_type, label in [
            ('integer', np.int32, 'integer[]', 'int32'),
            ('float8', np.float64, 'float8[]', 'float64'),
        ]:
            tbl = f'_bench_{label}'
            _create_pg_temp_table(
                conn,
                n_elements,
                shape_dims,
                dtype_sql,
                tbl,
            )

            text_q = f'COPY (SELECT arr FROM {tbl}) TO STDOUT'
            bin_q = f'COPY (SELECT arr FROM {tbl}) TO STDOUT WITH BINARY'

            # Fewer iterations for large sizes
            n = max(
                1,
                TIMEIT_NUMBER
                // max(
                    1,
                    n_elements // 1_000_000,
                ),
            )

            # Separate connections for fair comparison
            ct = psycopg.connect(
                conn_info,
                autocommit=True,
            )
            cc = psycopg.connect(
                conn_info,
                autocommit=True,
            )
            try:
                pt = _time_it(
                    lambda c=ct, q=text_q, d=np_dtype, p=pg_type: (
                        _pg_text_copy_to_numpy(c, q, d, p)
                    ),
                    n,
                )
                st = _time_it(
                    lambda c=cc, q=bin_q, p=pg_type: _pg_numpy_loader(c, q, p),
                    n,
                )
            finally:
                ct.close()
                cc.close()

            key = f'{label} {shape_name}'
            results[key] = (pt, st)

            conn.execute(  # type: ignore[union-attr]
                f'DROP TABLE IF EXISTS {tbl}'
            )
    finally:
        conn.close()

    return results


# ---------------------------------------------------------------------------
# Dedup: merge lines that are within threshold
# ---------------------------------------------------------------------------


def _dedup_lines(
    lines: dict[str, list[tuple[float, float]]],
) -> dict[str, list[tuple[float, float]]]:
    """Merge lines whose speedups are all within threshold.

    Returns a new dict where similar lines are merged
    under a combined label like "int32 1D/2D/3D".
    """
    keys = list(lines.keys())
    merged: dict[str, list[tuple[float, float]]] = {}
    used: set[str] = set()

    for i, k1 in enumerate(keys):
        if k1 in used:
            continue
        group = [k1]
        for k2 in keys[i + 1 :]:
            if k2 in used:
                continue
            if len(lines[k1]) != len(lines[k2]):
                continue
            all_close = all(
                abs((a[0] / a[1]) - (b[0] / b[1])) / max(a[0] / a[1], 0.001)
                < DEDUP_THRESHOLD
                for a, b in zip(
                    lines[k1],
                    lines[k2],
                    strict=True,
                )
            )
            if all_close:
                group.append(k2)
                used.add(k2)
        used.add(k1)

        label = '/'.join(group) if len(group) > 1 else group[0]
        merged[label] = lines[k1]

    return merged


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_size(n: int) -> str:
    """Format element count as short label."""
    if n >= 1_000_000:
        return f'{n // 1_000_000}M'
    if n >= 1_000:
        return f'{n // 1_000}K'
    return str(n)


def _fmt_time(seconds: float) -> str:
    """Format a time value for display."""
    if seconds >= 1:
        return f'{seconds:.2f} s'
    return f'{seconds * 1000:.1f} ms'


# ---------------------------------------------------------------------------
# SVG bar chart generation
# ---------------------------------------------------------------------------


def _generate_bar_chart_svg(
    output_path: pathlib.Path,
    title: str,
    labels: list[str],
    pure_times: list[float],
    fast_times: list[float],
    unit: str,
) -> None:
    """Generate a hand-crafted SVG bar chart."""
    n = len(labels)
    group_w = 120
    bar_w = 45
    gap = 10
    # Fixed width so all charts render at the same scale
    chart_w = 420
    chart_h = 260
    bar_area_top = 80
    bar_area_bot = 210
    bar_area_h = bar_area_bot - bar_area_top
    bars_offset = (chart_w - n * group_w) / 2

    display = [
        (
            t * 1000 if unit == 'ms' else t,
            f * 1000 if unit == 'ms' else f,
        )
        for t, f in zip(pure_times, fast_times, strict=True)
    ]
    max_val = max(d[0] for d in display)

    lines: list[str] = []
    a = lines.append

    a(
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="0 0 {chart_w} {chart_h}">'
    )
    a('  <style>')
    a('    .title { font: bold 16px system-ui, sans-serif; fill: #000; }')
    a('    .label { font: bold 13px system-ui, sans-serif; fill: #000; }')
    a('    .value { font: bold 10px system-ui, sans-serif; fill: white; }')
    a('    .speedup { font: bold 13px system-ui, sans-serif; fill: #047857; }')
    a('    .legend { font: 12px system-ui, sans-serif; fill: #000; }')
    a('  </style>')

    # Title
    cx = chart_w / 2
    a(
        f'  <text x="{cx}" y="22"'
        f' text-anchor="middle" class="title">'
        f'{title}</text>'
    )

    # Legend
    lx = cx - 75
    a(
        f'  <rect x="{lx}" y="36" width="12"'
        f' height="12" rx="2" fill="#f97316"/>'
    )
    a(f'  <text x="{lx + 16}" y="47" class="legend">Pure Python</text>')
    a(
        f'  <rect x="{lx + 110}" y="36" width="12"'
        f' height="12" rx="2" fill="#10b981"/>'
    )
    a(f'  <text x="{lx + 126}" y="47" class="legend">speedups</text>')

    # Bars
    for i, (lbl, (pv, fv)) in enumerate(zip(labels, display, strict=True)):
        gcx = bars_offset + i * group_w + group_w / 2
        ph = max(bar_area_h * pv / max_val, 16)
        fh = max(bar_area_h * fv / max_val, 16)
        py = bar_area_bot - ph
        fy = bar_area_bot - fh

        # Label
        a(
            f'  <text x="{gcx}" y="{bar_area_top - 4}"'
            f' text-anchor="middle" class="label">'
            f'{lbl}</text>'
        )

        # Pure Python bar (orange)
        px = gcx - bar_w - gap / 2
        a(
            f'  <rect x="{px}" y="{py:.1f}"'
            f' width="{bar_w}" height="{ph:.1f}"'
            f' rx="4" fill="#f97316"/>'
        )
        a(
            f'  <text x="{px + bar_w / 2}"'
            f' y="{py + ph / 2 + 4:.1f}"'
            f' text-anchor="middle" class="value">'
            f'{_fmt_time(pv / 1000 if unit == "ms" else pv)}'
            f'</text>'
        )

        # speedups bar (green)
        fx = gcx + gap / 2
        a(
            f'  <rect x="{fx}" y="{fy:.1f}"'
            f' width="{bar_w}" height="{fh:.1f}"'
            f' rx="4" fill="#10b981"/>'
        )
        a(
            f'  <text x="{fx + bar_w / 2}"'
            f' y="{fy + fh / 2 + 4:.1f}"'
            f' text-anchor="middle" class="value">'
            f'{_fmt_time(fv / 1000 if unit == "ms" else fv)}'
            f'</text>'
        )

        # Speedup factor
        speedup = pv / fv
        a(
            f'  <text x="{gcx}" y="{chart_h - 18}"'
            f' text-anchor="middle" class="speedup">'
            f'{speedup:.1f}'
            f'\N{MULTIPLICATION SIGN}</text>'
        )

    a('</svg>')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    py = f'{sys.version_info.major}.{sys.version_info.minor}'

    # --- STL ---
    print(f'Python {py} — STL benchmarks')
    print('=' * 50)

    stl_results: dict[int, dict[str, tuple[float, float]]] = {}

    for size in STL_SIZES:
        print(f'  {size:,} facets...')
        r = benchmark_stl(size)
        stl_results[size] = r
        for op, (pt, ct) in r.items():
            speedup = pt / ct
            fp, fc = _fmt_time(pt), _fmt_time(ct)
            print(f'    {op}: {fp} → {fc} ({speedup:.1f}x)')

    # Generate STL bar chart SVG at representative size
    if STL_CHART_SIZE in stl_results:
        chart_data = stl_results[STL_CHART_SIZE]
        _generate_bar_chart_svg(
            RESULTS_DIR / 'stl_performance.svg',
            f'STL I/O — {_fmt_size(STL_CHART_SIZE)} Facets',
            list(chart_data.keys()),
            [v[0] for v in chart_data.values()],
            [v[1] for v in chart_data.values()],
            'ms',
        )
        print(f'\n  STL chart saved to {RESULTS_DIR / "stl_performance.svg"}')

    # Print STL markdown table
    print('\n  STL Markdown table:')
    print('  | Operation | Facets | Pure Python | speedups | Speedup |')
    print('  |:----------|-------:|------------:|---------:|--------:|')
    for size in STL_SIZES:
        for op, (pt, ct) in stl_results[size].items():
            speedup = pt / ct
            print(
                f'  | {op} | {size:,} '
                f'| {_fmt_time(pt)} | {_fmt_time(ct)} '
                f'| **{speedup:.1f}x** |'
            )

    # --- PG ---
    conn_info = _ensure_pg()

    if conn_info is not None:
        print()
        print(f'Python {py} — PG benchmarks')
        print('=' * 50)

        pg_raw: dict[str, list[tuple[float, float]]] = {}

        for size in PG_SIZES:
            print(f'  {size:,} elements...')
            for sname, sdims in PG_SHAPES:
                r = benchmark_pg(
                    conn_info,
                    size,
                    sname,
                    sdims,
                )
                for key, times in r.items():
                    pg_raw.setdefault(key, [])
                    pg_raw[key].append(times)
                    speedup = times[0] / times[1]
                    print(
                        f'    {key}: {_fmt_time(times[0])} → '
                        f'{_fmt_time(times[1])} ({speedup:.1f}x)'
                    )

        pg_deduped = _dedup_lines(pg_raw)

        # Generate PG bar chart SVG at representative size
        # Use one entry per base type (first deduped group wins)
        pg_chart_idx = PG_SIZES.index(PG_CHART_SIZE)
        chart_labels: list[str] = []
        chart_pure: list[float] = []
        chart_fast: list[float] = []
        seen_base: set[str] = set()
        for label, vals in pg_deduped.items():
            base = label.split()[0]
            if base in seen_base:
                continue
            seen_base.add(base)
            chart_labels.append(base)
            chart_pure.append(vals[pg_chart_idx][0])
            chart_fast.append(vals[pg_chart_idx][1])

        _generate_bar_chart_svg(
            RESULTS_DIR / 'pg_array_performance.svg',
            f'PostgreSQL COPY → NumPy — {_fmt_size(PG_CHART_SIZE)} Elements',
            chart_labels,
            chart_pure,
            chart_fast,
            's',
        )
        print(
            f'\n  PG chart saved to {RESULTS_DIR / "pg_array_performance.svg"}'
        )

        # Print PG markdown table (1D shape as representative)
        print('\n  PG Markdown table:')
        print('  | Type | Elements | Pure Python | speedups | Speedup |')
        print('  |:-----|:---------|------------:|---------:|--------:|')
        for key, vals in pg_raw.items():
            if not key.endswith(' 1D'):
                continue
            base = key.split()[0]
            for i, size in enumerate(PG_SIZES):
                pt, ct = vals[i]
                speedup = pt / ct
                print(
                    f'  | {base} | {_fmt_size(size)} '
                    f'| {_fmt_time(pt)} | {_fmt_time(ct)} '
                    f'| **{speedup:.1f}x** |'
                )
    else:
        print('  Skipping PG benchmarks.')

    print('\nDone.')


if __name__ == '__main__':
    main()
