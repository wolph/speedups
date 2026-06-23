"""Integration tests for the FastBarIterator accelerator.

Cython modules can't be measured by Python coverage, so the iterator is tested
indirectly through a fake bar that implements the protocol it drives
(``_fast_begin``/``_fast_tick``/``_fast_end``/``_fast_end_dirty`` plus the
``value``/``_next_update``/``_finished`` attributes). This mirrors how
``progressbar.ProgressBar`` uses it without depending on that package.
"""

import gc

from speedups.progressbar import FastBarIterator


class FakeBar:
    """Minimal stand-in for ProgressBar implementing the fast protocol."""

    def __init__(self, step: int = 5) -> None:
        self.value = 0
        self._next_update = 0
        self._finished = False
        self.step = step
        self.ticks: list[int] = []
        self.began = False
        self.ended: str | None = None

    def _fast_begin(self) -> None:
        self.began = True
        self.value = 0
        self._next_update = self.value + self.step

    def _fast_tick(self, value: int) -> None:
        self.value = value
        self.ticks.append(value)
        self._next_update = value + self.step

    def _fast_end(self) -> None:
        self._finished = True
        self.ended = 'clean'

    def _fast_end_dirty(self) -> None:
        self._finished = True
        self.ended = 'dirty'


def test_yields_all_items_in_order():
    bar = FakeBar(step=5)
    out = list(FastBarIterator(bar, range(20)))
    assert out == list(range(20))
    assert bar.began
    assert bar.ended == 'clean'
    # First item is yielded at value 0 (no count); last at n-1, like the bar.
    assert bar.value == 19


def test_ticks_only_at_crossings():
    bar = FakeBar(step=5)
    list(FastBarIterator(bar, range(21)))
    # First item uncounted; count runs 1..20, crossing the step every 5.
    assert bar.ticks == [5, 10, 15, 20]


def test_empty_iterable_begins_and_ends_clean():
    bar = FakeBar()
    assert list(FastBarIterator(bar, [])) == []
    assert bar.began
    assert bar.ended == 'clean'
    assert bar.ticks == []


def test_exhaustion_finishes_clean():
    bar = FakeBar()
    list(FastBarIterator(bar, range(3)))
    assert bar.ended == 'clean'
    assert bar._finished


def test_break_finishes_dirty_on_dealloc():
    bar = FakeBar(step=5)
    it = FastBarIterator(bar, range(1000))
    collected = []
    for x in it:
        collected.append(x)
        if x == 7:
            break
    assert collected == list(range(8))
    del it
    gc.collect()
    assert bar.ended == 'dirty'
    assert bar._finished


def test_non_sequence_iterable():
    bar = FakeBar(step=3)

    def gen():
        yield from range(10)

    assert list(FastBarIterator(bar, gen())) == list(range(10))
    assert bar.ended == 'clean'
