# cython: language_level=2
# NOTE: language_level=2 is intentional — this module uses C string
# operations (strstr, strcmp, sscanf, fprintf) with string literals that
# must be bytes, not unicode. The per-file directive overrides the
# global language_level=3 in setup.py.
from libc.stdio cimport *
from libc.string cimport memcpy, strcmp, strstr

cdef extern from '_platform.h':
    int dup(int fd)

    ctypedef void* spd_locale_t
    spd_locale_t spd_create_c_locale()
    spd_locale_t spd_uselocale(spd_locale_t)
    void spd_freelocale(spd_locale_t)

import numpy as np
cimport numpy as np

np.import_array()

cdef packed struct Facet:
    np.float32_t n[3]
    np.float32_t v[3][3]
    np.uint16_t attr

dtype = np.dtype([
    ('normals', np.float32, 3),
    ('vectors', np.float32, (3, 3)),
    ('attr', np.uint16, (1,)),
])

DEF ALLOC_SIZE = 200000
DEF BUF_SIZE = 8192
DEF LINE_SIZE = 8192

cdef struct s_State:
    FILE* fp
    char buf[BUF_SIZE]
    char line[LINE_SIZE]
    size_t pos
    size_t size
    size_t line_num
    int recoverable

ctypedef s_State State

cdef char* readline(State* state) except NULL:

    cdef size_t line_pos = 0
    cdef char current;
    while True:
        if state.pos == state.size:
            if feof(state.fp):
                if line_pos != 0:
                    state.line[line_pos] = '\0'
                    return state.line
                raise RuntimeError(state.recoverable, 'Unexpected EOF')

            state.size = fread(state.buf, 1, BUF_SIZE, state.fp)
            state.pos = 0
            state.recoverable = 0

        if line_pos == LINE_SIZE:
            raise RuntimeError(
                state.recoverable, 'Line longer than %d, probably non-ascii' %
                LINE_SIZE)

        current = state.buf[state.pos]
        state.pos += 1

        if line_pos != 0 or (current != ' ' \
                and current != '\t' \
                and current != '\r'):
            if current == '\n':
                state.line_num += 1
                if line_pos != 0:
                    state.line[line_pos] = '\0'
                    return state.line
            elif 0x40 < current < 0x5b:
                # Change all ascii characters to lower case
                state.line[line_pos] = current | 0x60
                line_pos += 1
            else:
                state.line[line_pos] = current
                line_pos += 1


def ascii_read(fh, buf):
    cdef char* line
    cdef char name[LINE_SIZE]
    cdef np.ndarray[Facet, cast=True] arr = np.zeros(ALLOC_SIZE, dtype = dtype)
    cdef size_t offset
    cdef Facet* facet = <Facet*>arr.data
    cdef size_t pos = 0
    cdef Py_ssize_t buf_len
    cdef State state

    state.fp = NULL

    cdef spd_locale_t new_locale = spd_create_c_locale()
    cdef spd_locale_t old_locale = spd_uselocale(new_locale)

    try:
        buf_len = len(buf)
        if buf_len > BUF_SIZE:
            raise ValueError(
                "ascii_read: initial buffer length %d exceeds internal buffer size %d"
                % (buf_len, BUF_SIZE))
        state.size = buf_len
        memcpy(state.buf, <char*> buf, state.size)
        state.pos = 0
        state.line_num = 0
        state.recoverable = 1
        state.fp = fdopen(dup(fh.fileno()), 'rb')
        if state.fp == NULL:
            raise OSError('Failed to open file descriptor')
        fseek(state.fp, fh.tell(), SEEK_SET)

        line = readline(&state)

        if strstr(line, 'solid') != line:
            raise RuntimeError(state.recoverable,
                    'Solid name not found (%i:%s)' % (state.line_num, line))

        snprintf(name, LINE_SIZE, "%s", line + 5)

        while True:

            line = readline(&state)

            if strstr(line, 'endsolid') != NULL \
                    or strstr(line, 'end solid') != NULL:
                arr.resize(facet - <Facet*>arr.data, refcheck=False)
                return (<object>name).strip(), arr

            if strcmp(line, 'color') == 0:
                readline(&state)
                continue
            elif sscanf(line, '%*s %*s %e %e %e',
                    facet.n, facet.n+1, facet.n+2) != 3:
                raise RuntimeError(state.recoverable,
                    'Cannot read normals (%i:%s)' % (state.line_num, line))

            readline(&state) # outer loop

            for i in range(3):
                line = readline(&state)
                if sscanf(line, '%*s %e %e %e',
                        facet.v[i], facet.v[i]+1, facet.v[i]+2) != 3:
                    raise RuntimeError(state.recoverable,
                        'Cannot read vertex (%i:%s)' % (state.line_num, line))

            readline(&state) # endloop
            readline(&state) # endfacet

            facet += 1
            offset = facet - <Facet*>arr.data
            if arr.shape[0] == offset:
                arr.resize(arr.shape[0] + ALLOC_SIZE, refcheck=False)
                facet = <Facet*>arr.data + offset

    finally:
        if state.fp != NULL:
            if state.recoverable == 0:
                pos = ftell(state.fp) - state.size + state.pos
            fclose(state.fp)
            if state.recoverable == 0:
                fh.seek(pos, SEEK_SET)

        spd_uselocale(old_locale)
        spd_freelocale(new_locale)


def ascii_write(fh, name, np.ndarray[Facet, mode = 'c', cast=True] arr):
    cdef FILE* fp = NULL
    cdef Facet* facet = <Facet*>arr.data
    cdef Facet* end = <Facet*>arr.data + arr.shape[0]
    cdef size_t pos = 0

    try:
        fp = fdopen(dup(fh.fileno()), 'wb')
        if fp == NULL:
            raise OSError('Failed to open file descriptor')
        fseek(fp, fh.tell(), SEEK_SET)
        fprintf(fp, 'solid %s\n', <char*>name)
        while facet != end:
            fprintf(fp, 
                'facet normal %f %f %f\n'
                '  outer loop\n'
                '    vertex %f %f %f\n'
                '    vertex %f %f %f\n'
                '    vertex %f %f %f\n'
                '  endloop\n'
                'endfacet\n',
                facet.n[0], facet.n[1], facet.n[2],
                facet.v[0][0], facet.v[0][1], facet.v[0][2],
                facet.v[1][0], facet.v[1][1], facet.v[1][2],
                facet.v[2][0], facet.v[2][1], facet.v[2][2])
            facet += 1
        fprintf(fp, 'endsolid %s\n', <char*>name)
    finally:
        if fp != NULL:
            pos = ftell(fp)
            fclose(fp)
            fh.seek(pos, SEEK_SET)
        
