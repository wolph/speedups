from typing import IO, Any

import numpy as np
import numpy.typing as npt

dtype: np.dtype[Any]

def ascii_read(
    fh: IO[bytes],
    buf: bytes,
) -> tuple[bytes, npt.NDArray[Any]]: ...
def ascii_write(
    fh: IO[bytes],
    name: bytes,
    arr: npt.NDArray[Any],
) -> None: ...
