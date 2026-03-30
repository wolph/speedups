from collections.abc import Callable
from typing import Any

import numpy as np
import numpy.typing as npt

ConverterT = Callable[[memoryview, npt.NDArray[Any]], None]

def float_array_to_numpy(
    data: memoryview,
    output_view: npt.NDArray[np.floating[Any]],
) -> None:
    pass

def int_array_to_numpy(
    data: memoryview,
    output_view: npt.NDArray[np.integer[Any]],
) -> None:
    pass
