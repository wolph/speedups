#!/usr/bin/env cythonize -X language_level=3 -a -i speedups.pyx

cimport cython
from libc cimport stdint

cimport numpy as np

from . cimport hton


np.import_array()


cdef extern from 'math.h':
    float NAN


ctypedef fused int_output_type:
    stdint.int16_t
    stdint.int32_t
    stdint.int64_t


ctypedef fused float_output_type:
    float
    double


@cython.boundscheck(False)
@cython.wraparound(False)
def float_array_to_numpy(
        const char[:] data,
        float_output_type[:] output_view,
):
    cdef Py_ssize_t i, count, pointer = 0
    cdef Py_ssize_t data_len = data.shape[0]
    cdef int size

    count = output_view.size

    with nogil:
        for i in range(count):
            if pointer + 4 > data_len:
                with gil:
                    raise ValueError(
                        'Malformed array data: truncated element header')
            size = hton.unpack_int32(&data[pointer])
            pointer += 4

            if size == -1:
                output_view[i] = NAN
                continue

            if size != 4 and size != 8:
                with gil:
                    raise TypeError(f'Unsupported output type with size {size}')
            if pointer + size > data_len:
                with gil:
                    raise ValueError(
                        'Malformed array data: truncated element')

            if size == 4:
                output_view[i] = hton.unpack_float(&data[pointer])
            else:
                output_view[i] = hton.unpack_double(&data[pointer])

            pointer += size

@cython.boundscheck(False)
@cython.wraparound(False)
def int_array_to_numpy(
        const char[:] data,
        int_output_type[:] output_view,
):
    cdef Py_ssize_t i, count, pointer = 0
    cdef Py_ssize_t data_len = data.shape[0]
    cdef int size

    count = output_view.size

    with nogil:
        for i in range(count):
            if pointer + 4 > data_len:
                with gil:
                    raise ValueError(
                        'Malformed array data: truncated element header')
            size = hton.unpack_int32(&data[pointer])
            pointer += 4

            if size == -1:
                with gil:
                    raise ValueError('NULL values are not supported')

            if size != 2 and size != 4 and size != 8:
                with gil:
                    raise TypeError(f'Unsupported output type with size {size}')
            if pointer + size > data_len:
                with gil:
                    raise ValueError(
                        'Malformed array data: truncated element')

            if size == 2:
                output_view[i] = hton.unpack_int16(&data[pointer])
            elif size == 4:
                output_view[i] = hton.unpack_int32(&data[pointer])
            else:
                output_view[i] = hton.unpack_int64(&data[pointer])

            pointer += size
