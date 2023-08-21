import numpy
import psycopg
import pytest

import speedups

print('speedups', speedups)
from speedups import psycopg_array  # noqa: E402

print('speedups', psycopg_array)
from speedups import psycopg_loaders  # noqa: E402


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
        copy.set_types(
            [
                'integer[]',
            ]
        )

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
        copy.set_types(
            [
                'float4[]',
                'float8[]',
                'smallint[]',
                'integer[]',
                'bigint[]',
            ]
        )

        totals = numpy.zeros(5, dtype=numpy.int8)
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
        copy.set_types(
            [
                'float4[]',
                'float8[]',
                'float4[]',
                'float8[]',
            ]
        )

        for row in copy.rows():
            assert row[0].dtype == numpy.float32
            assert row[1].dtype == numpy.float32
            assert row[2].dtype == numpy.float64
            assert row[3].dtype == numpy.float64
            for column in row:
                assert column.sum() == pytest.approx(0.3)


def test_types(postgresql: psycopg.Connection):
    cursor: psycopg.Cursor = postgresql.cursor(binary=True)
    psycopg_loaders.NumpyLoader.install(cursor)

    query = r'''
    COPY (
        SELECT
            '{0.1, 0.2}'::float4[],
            '{0.1, 0.2}'::float8[],
            '{1, 2}'::int2[],
            '{1, 2}'::int4[],
            '{1, 2}'::int8[],
            '{"a", "b"}'::text[],
            '{"a", "b"}'::varchar[],
            0.1::float4,
            1::int4,
            'a'::text
    ) TO STDOUT WITH BINARY
    '''

    copy: psycopg.Copy
    with cursor.copy(query) as copy:
        print('running query', query)
        copy.set_types(
            [
                'float4[]',
                'float8[]',
                'int2[]',
                'int4[]',
                'int8[]',
                'text[]',
                'varchar[]',
                'float4',
                'int4',
                'text',
            ]
        )

        for row in copy.rows():
            assert row[0].dtype == numpy.float32
            assert row[0].sum() == pytest.approx(0.3)
            assert row[1].dtype == numpy.float64
            assert row[1].sum() == pytest.approx(0.3)

            assert row[2].dtype == numpy.int16
            assert row[2].sum() == pytest.approx(3)
            assert row[3].dtype == numpy.int32
            assert row[3].sum() == pytest.approx(3)
            assert row[4].dtype == numpy.int64
            assert row[4].sum() == pytest.approx(3)

            assert row[5] == ['a', 'b']
            assert row[6] == ['a', 'b']

            assert row[7] == pytest.approx(0.1)
            assert row[8] == 1
            assert row[9] == 'a'
