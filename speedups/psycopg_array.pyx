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
    cdef int i, size, count, pointer = 0

    count = output_view.size

    with nogil:
        for i in range(count):
            size = hton.unpack_int32(&data[pointer])
            pointer += 4

            if size == -1:
                output_view[i] = NAN
                continue
            elif size == 4:
                output_view[i] = hton.unpack_float(&data[pointer])
            elif size == 8:
                output_view[i] = hton.unpack_double(&data[pointer])
            else:
                with gil:
                    raise TypeError(f'Unsupported output type with size {size}')

            pointer += size

@cython.boundscheck(False)
@cython.wraparound(False)
def int_array_to_numpy(
        const char[:] data,
        int_output_type[:] output_view,
):
    cdef int i, size, count, pointer = 0

    count = output_view.size

    with nogil:
        for i in range(count):
            size = hton.unpack_int32(&data[pointer])
            pointer += 4

            if size == -1:
                with gil:
                    raise ValueError('NULL values are not supported')
            elif size == 2:
                output_view[i] = hton.unpack_int16(&data[pointer])
            elif size == 4:
                output_view[i] = hton.unpack_int32(&data[pointer])
            elif size == 8:
                output_view[i] = hton.unpack_int64(&data[pointer])
            else:
                with gil:
                    raise TypeError(f'Unsupported output type with size {size}')

            pointer += size
