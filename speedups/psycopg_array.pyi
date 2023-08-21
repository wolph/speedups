from typing import Any, Callable
import numpy as np
import numpy.typing as npt

converterT = Callable[[memoryview, npt.NDArray[Any]], None]

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
