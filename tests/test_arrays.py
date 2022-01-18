import psycopg

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
