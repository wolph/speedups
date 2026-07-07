# ASCII STL I/O

`speedups.stl` contains low-level ASCII STL parsing and writing helpers. The
module is built for projects that already use the structured NumPy mesh layout
from `numpy-stl`.

Most applications should use [numpy-stl](https://github.com/WoLpH/numpy-stl)
directly for full STL file handling. Use `speedups.stl` when you need the
low-level parser or writer and already have the expected mesh array.

## Mesh Dtype

The parser returns, and the writer expects, a structured NumPy array with this
shape:

```python
import numpy as np

mesh_dtype = np.dtype(
    [
        ("normals", np.float32, 3),
        ("vectors", np.float32, (3, 3)),
        ("attr", np.uint16, (1,)),
    ]
)
```

Each row is one facet:

- `normals`: the facet normal vector.
- `vectors`: the three vertex vectors.
- `attr`: the STL attribute field used by the `numpy-stl` layout.

## Reading ASCII STL

Read an initial buffer from the binary file handle, then pass the same handle
and buffer to `ascii_read()`:

```python
from speedups.stl import ascii_read

with open("model.stl", "rb") as fh:
    buffer = fh.read(8192)
    name, mesh = ascii_read(fh, buffer)

print(name.strip())
print(mesh.dtype)
print(mesh["vectors"].shape)
```

`ascii_read()` expects the file handle to be positioned immediately after the
initial buffer read. It returns the STL solid name as `bytes` and the parsed
facet array.

Malformed ASCII STL input raises `RuntimeError`. Very long lines are rejected
rather than silently truncated.

## Writing ASCII STL

Pass a binary file handle, a bytes solid name, and a mesh array using the dtype
above:

```python
import numpy as np

from speedups.stl import ascii_write

mesh_dtype = np.dtype(
    [
        ("normals", np.float32, 3),
        ("vectors", np.float32, (3, 3)),
        ("attr", np.uint16, (1,)),
    ]
)

mesh = np.zeros(1, dtype=mesh_dtype)
mesh["normals"][0] = [0.0, 0.0, 1.0]
mesh["vectors"][0] = [
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
]

with open("triangle.stl", "wb") as fh:
    ascii_write(fh, b"triangle", mesh)
```

The writer emits ASCII STL text to the binary handle.

## API Reference

```python
ascii_read(fh: typing.IO[bytes], buf: bytes) -> tuple[bytes, np.ndarray]
```

Reads ASCII STL data from `fh`, using `buf` as the already-read initial data.

```python
ascii_write(fh: typing.IO[bytes], name: bytes, arr: np.ndarray) -> None
```

Writes `arr` to `fh` as an ASCII STL solid named `name`.
