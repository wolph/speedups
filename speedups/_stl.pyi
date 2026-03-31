"""Low-level ASCII STL I/O used internally by numpy-stl.

For reading and writing STL files, use numpy-stl:
https://github.com/WoLpH/numpy-stl
"""

from typing import IO, Any

import numpy as np
import numpy.typing as npt

dtype: np.dtype[Any]

def ascii_read(
    fh: IO[bytes],
    buf: bytes,
) -> tuple[bytes, npt.NDArray[np.void]]: ...
def ascii_write(
    fh: IO[bytes],
    name: bytes,
    arr: npt.NDArray[np.void],
) -> None: ...
