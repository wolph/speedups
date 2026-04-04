import pathlib
import tempfile

import numpy as np
import pytest

from speedups import ascii_read, ascii_write

DTYPE = np.dtype([
    ('normals', np.float32, 3),
    ('vectors', np.float32, (3, 3)),
    ('attr', np.uint16, (1,)),
])

STL_ASCII_DIR = pathlib.Path(__file__).parent.parent.parent / 'numpy-stl' / 'tests' / 'stl_ascii'

ASCII_FILES = sorted(STL_ASCII_DIR.glob('*.stl')) if STL_ASCII_DIR.exists() else []


@pytest.fixture(params=[f.name for f in ASCII_FILES], ids=[f.stem for f in ASCII_FILES])
def ascii_stl(request):
    return STL_ASCII_DIR / request.param


SIMPLE_STL = b"""\
solid test
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 1.0 0.0 0.0
      vertex 0.0 1.0 0.0
    endloop
  endfacet
endsolid test
"""


def test_ascii_read_simple():
    with tempfile.NamedTemporaryFile(suffix='.stl') as f:
        f.write(SIMPLE_STL)
        f.flush()
        f.seek(0)
        buf = f.read(8192)
        f.seek(0)
        name, data = ascii_read(f, buf)
        assert name.strip() == b'test'
        assert len(data) == 1
        np.testing.assert_array_almost_equal(
            data['normals'][0], [0.0, 0.0, 1.0],
        )
        np.testing.assert_array_almost_equal(
            data['vectors'][0][0], [0.0, 0.0, 0.0],
        )
        np.testing.assert_array_almost_equal(
            data['vectors'][0][1], [1.0, 0.0, 0.0],
        )
        np.testing.assert_array_almost_equal(
            data['vectors'][0][2], [0.0, 1.0, 0.0],
        )


def test_ascii_write_simple():
    arr = np.zeros(1, dtype=DTYPE)
    arr['normals'][0] = [0.0, 0.0, 1.0]
    arr['vectors'][0] = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    with tempfile.NamedTemporaryFile(suffix='.stl', mode='w+b') as f:
        ascii_write(f, b'test', arr)
        f.seek(0)
        content = f.read().decode('ascii')
        assert 'solid test' in content
        assert 'endsolid test' in content
        assert 'facet normal' in content
        assert 'vertex' in content


def test_roundtrip():
    """Write then read back and verify data matches."""
    arr = np.zeros(3, dtype=DTYPE)
    arr['normals'][0] = [1.0, 0.0, 0.0]
    arr['normals'][1] = [0.0, 1.0, 0.0]
    arr['normals'][2] = [0.0, 0.0, 1.0]
    for i in range(3):
        arr['vectors'][i] = [
            [float(i), 0.0, 0.0],
            [0.0, float(i + 1), 0.0],
            [0.0, 0.0, float(i + 2)],
        ]

    with tempfile.NamedTemporaryFile(suffix='.stl', mode='w+b') as f:
        ascii_write(f, b'roundtrip', arr)
        f.seek(0)
        buf = f.read(8192)
        f.seek(0)
        name, data = ascii_read(f, buf)
        assert name.strip() == b'roundtrip'
        assert len(data) == 3
        np.testing.assert_array_almost_equal(
            data['normals'], arr['normals'], decimal=5,
        )
        np.testing.assert_array_almost_equal(
            data['vectors'], arr['vectors'], decimal=5,
        )


@pytest.mark.skipif(not ASCII_FILES, reason='numpy-stl test fixtures not found')
def test_ascii_read_fixture(ascii_stl):
    """Read real STL files from numpy-stl test suite."""
    with open(ascii_stl, 'rb') as f:
        buf = f.read(8192)
        # ascii_read expects fh positioned after the initial buffer read
        name, data = ascii_read(f, buf)
        assert isinstance(name, bytes)
        assert len(data) > 0
        assert data.dtype == DTYPE
