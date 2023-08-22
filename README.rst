Speedups
------------------------------------------------------------------------------

.. image:: https://github.com/wolph/speedups/actions/workflows/build_wheels.yml/badge.svg
   :target: https://github.com/wolph/speedups/actions/workflows/build_wheels.yml

.. image:: https://github.com/wolph/speedups/actions/workflows/tox.yml/badge.svg
   :target: https://github.com/wolph/speedups/actions/workflows/tox.yml

This library contains a number of functions for speeding up critical parts
of your Python code without having to bother with the hassle of building
binary extensions. That way you can keep your main packages simple `PEP517`_
based packages and still get the speedups.

Currently only a few functions are available, but several more are planned.

Generic endian conversion functions in `speedups.hton`_:

- ``void pack_int16(char *buf, int16_t x)``
- ``void pack_int32(char *buf, int32_t x)``
- ``void pack_int64(char *buf, int64_t x)``
- ``void pack_float(char *buf, float f)``
- ``void pack_double(char *buf, double f)``
- ``int16_t unpack_int16(const char *buf)``
- ``uint16_t unpack_uint16(const char *buf)``
- ``int32_t unpack_int32(const char *buf)``
- ``uint32_t unpack_uint32(const char *buf)``
- ``int64_t unpack_int64(const char *buf)``
- ``uint64_t unpack_uint64(const char *buf)``
- ``float unpack_float(const char *buf)``
- ``double unpack_double(const char *buf)``

These functions are used to convert between native and network byte order and
are meant to be used from Cython code. Examples can be found in the
`speedups.psycopg_array`_ code.

For the psycopg library we have a binary `COPY`_ loader_ to convert a
PostgreSQL array to a `numpy`_  ``ndarray``. This can be used with the ``copy()``
method of a psycopg cursor: https://www.psycopg.org/psycopg3/docs/basic/copy.html

It supports the following PostgreSQL types:

- ``float4`` (``numpy.float32``)
- ``float8`` (``numpy.float64``)
- ``smallint`` (``numpy.int16``)
- ``integer`` (``numpy.int32``)
- ``bigint`` (``numpy.int64``)

Additionally, it supports arrays varying from 1D to N-D so a 2D or 3D array
are supported.

.. code-block:: python

    cursor: psycopg.Cursor
    psycopg_loaders.NumpyLoader.install(cursor)

    query = '''
    COPY (
        SELECT array_agg(x)
        FROM generate_series(1, 100000) x
    ) TO STDOUT WITH BINARY
    '''

    copy: psycopg.Copy
    with cursor.copy(query) as copy:
        copy.set_types(['integer[]'])

        for row in copy.rows():
            print(row)

.. _numpy: http://www.numpy.org/
.. _COPY: https://www.postgresql.org/docs/current/static/sql-copy.html
.. _speedups.hton: https://github.com/WoLpH/speedups/blob/master/speedups/hton.pxd
.. _speedups.psycopg_array: https://github.com/WoLpH/speedups/blob/master/speedups/psycopg_array.pyx
.. _loader: https://github.com/WoLpH/speedups/blob/master/speedups/psycopg_loaders.py
.. _pep517: https://www.python.org/dev/peps/pep-0517/
