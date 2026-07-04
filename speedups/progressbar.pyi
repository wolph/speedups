"""Native iterator accelerator for python-progressbar.

Used automatically by ``progressbar2[fast]`` (``progressbar.ProgressBar``
imports ``FastBarIterator`` when this package is installed). The bar must
implement the small protocol consumed by ``__next__``: ``_fast_begin()``,
``_fast_tick(value)``, ``_fast_end()``, ``_fast_end_dirty()`` and the plain
attributes ``value``, ``_next_update`` and ``_finished``.
"""

import typing

class FastBarIterator:
    """Iterates ``iterable``, driving ``bar`` and counting in a C field.

    Only ``bar.value`` is written back, and only at redraw crossings
    (~20x/sec, like ``tqdm.n``) and once more at finish, so the per-item loop
    does no Python attribute writes. ``previous_value`` (and any other bar
    state) is maintained by the bar itself inside its
    ``_fast_tick()``/``_fast_end()`` hooks.
    """

    def __init__(
        self,
        bar: typing.Any,
        iterable: typing.Iterable[typing.Any],
    ) -> None: ...
    def __iter__(self) -> FastBarIterator: ...
    def __next__(self) -> typing.Any: ...
