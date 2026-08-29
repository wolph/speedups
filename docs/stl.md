# ASCII STL I/O

`speedups.stl` exposes the low-level parser and writer used by `numpy-stl`.
Both functions work with the structured NumPy mesh layout from that project.

Most applications should use [numpy-stl](https://github.com/WoLpH/numpy-stl)
for complete STL file handling. I would call `speedups.stl` directly only when
the surrounding application already owns the file handling and mesh API.

## Mesh dtype

The parser returns, and the writer expects, one structured NumPy row per facet.
Define the dtype like this:

```python
import numpy as np

mesh_dtype = np.dtype(
    [
        ('normals', np.float32, 3),
        ('vectors', np.float32, (3, 3)),
        ('attr', np.uint16, (1,)),
    ]
)
```

The three fields map directly to one STL facet:

- `normals`: the facet normal vector.
- `vectors`: the three vertex vectors.
- `attr`: the STL attribute field used by the `numpy-stl` layout.

## Reading ASCII STL

`ascii_read()` accepts an initial buffer so callers can inspect a file before
choosing the ASCII parser. Read at most 8192 bytes, then pass the same handle
and buffer to the parser:

```python
from speedups.stl import ascii_read

with open('model.stl', 'rb') as fh:
    buffer = fh.read(8192)
    name, mesh = ascii_read(fh, buffer)

print(name.strip())
print(mesh.dtype)
print(mesh['vectors'].shape)
```

The first printed value is the STL solid name as `bytes`. ASCII uppercase
characters are normalized to lowercase while parsing, including characters in
the solid name. The dtype is the structured layout above, and
`mesh['vectors']` has shape `(facets, 3, 3)`. The parser expects the file handle
to remain positioned immediately after the initial read.

> [!NOTE]
> The initial buffer cannot exceed 8192 bytes. Malformed input and lines longer
> than the internal limit raise an exception instead of being silently
> truncated.

## Writing ASCII STL

The writer needs a binary file handle, a `bytes` solid name, and a contiguous
mesh array using the dtype above:

```python
import numpy as np

from speedups.stl import ascii_write

mesh_dtype = np.dtype(
    [
        ('normals', np.float32, 3),
        ('vectors', np.float32, (3, 3)),
        ('attr', np.uint16, (1,)),
    ]
)

mesh = np.zeros(1, dtype=mesh_dtype)
mesh['normals'][0] = [0.0, 0.0, 1.0]
mesh['vectors'][0] = [
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
]

with open('triangle.stl', 'wb') as fh:
    ascii_write(fh, b'triangle', mesh)
```

The resulting file starts with `solid triangle`, contains one `facet` block,
and ends with `endsolid triangle`. The handle remains positioned after the
written data.

## API Reference

```python
ascii_read(fh, buf: bytes) -> tuple[bytes, np.ndarray]
```

Reads ASCII STL data from `fh`, using `buf` as the already-read initial data.
The handle must be a seekable binary file backed by an OS file descriptor. The
implementation calls `fileno()`, `tell()`, and `seek()`, so `io.BytesIO` is not
accepted.

```python
ascii_write(fh, name: bytes, arr: np.ndarray) -> None
```

Writes `arr` to `fh` as an ASCII STL solid named `name`. The handle has the same
file descriptor and seek requirements as `ascii_read()`.
