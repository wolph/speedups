import typing
import numpy as np

converterT = typing.Callable[[memoryview, np.ndarray[typing.Any, typing.Any]], None]

def float_array_to_numpy(
        data: memoryview,
        output_view: np.ndarray[np.float32 | np.float64, typing.Any],
) -> None:
    pass


def int_array_to_numpy(
        data: memoryview,
        output_view: np.ndarray[np.int16 | np.int32 | np.int64, typing.Any],
) -> None:
    pass

