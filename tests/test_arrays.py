import numpy
import psycopg
import pytest

import speedups
print('speedups', speedups)
from speedups import psycopg_array
print('speedups', psycopg_array)
from speedups import psycopg_loaders


def test_1d(postgresql: psycopg.Connection):
    cursor: psycopg.Cursor = postgresql.cursor(binary=True)
    psycopg_loaders.NumpyLoader.install(cursor)

    query = '''
    COPY (
        SELECT array_agg(x)
        FROM generate_series(1, 100000) x
    ) TO STDOUT WITH BINARY
    '''

    copy: psycopg.Copy
    with cursor.copy(query) as copy:
        print('running query', query)
        copy.set_types([
            'integer[]',
        ])

        total = 0
        for row in copy.rows():
            total += row[0].sum()

    assert total == 5000050000


def test_2d(postgresql: psycopg.Connection):
    cursor: psycopg.Cursor = postgresql.cursor(binary=True)
    psycopg_loaders.NumpyLoader.install(cursor)

    query = '''
    COPY (
        SELECT
            '{{0.1, 0.2}, {0.3, 0.4}}'::float4[][],
            '{{0.1, 0.2}, {0.3, 0.4}}'::float8[][],
            '{{1, 2}, {3, 4}}'::smallint[][],
            '{{1, 2}, {3, 4}}'::integer[][],
            '{{1, 2}, {3, 4}}'::bigint[][]
    ) TO STDOUT WITH BINARY
    '''

    copy: psycopg.Copy
    with cursor.copy(query) as copy:
        print('running query', query)
        copy.set_types([
            'float4[]',
            'float8[]',
            'smallint[]',
            'integer[]',
            'bigint[]',
        ])

        totals = [0] * 5
        for row in copy.rows():
            for i, column in enumerate(row):
                totals[i] += column.sum()

    for total in totals[:2]:
        assert total.sum() == 1.0

    for total in totals[3:]:
        assert total.sum() == 10


def test_cast(postgresql: psycopg.Connection):
    cursor: psycopg.Cursor = postgresql.cursor(binary=True)
    psycopg_loaders.NumpyLoader.install(cursor)

    query = '''
    COPY (
        SELECT
            '{0.1, 0.2}'::float4[],
            '{0.1, 0.2}'::float4[],
            '{0.1, 0.2}'::float8[],
            '{0.1, 0.2}'::float8[]
    ) TO STDOUT WITH BINARY
    '''

    copy: psycopg.Copy
    with cursor.copy(query) as copy:
        print('running query', query)
        copy.set_types([
            'float4[]',
            'float8[]',
            'float4[]',
            'float8[]',
        ])

        for row in copy.rows():
            assert row[0].dtype == numpy.float32
            assert row[1].dtype == numpy.float32
            assert row[2].dtype == numpy.float64
            assert row[3].dtype == numpy.float64
            for column in row:
                assert column.sum() == pytest.approx(0.3)
