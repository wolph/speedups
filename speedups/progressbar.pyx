# cython: language_level=3, boundscheck=False, wraparound=False
"""Progressbar-tailored fast iterator.

The item count lives in a C field; the per-item loop does no Python attribute
writes. The iterator writes back only ``bar.value``, and only at redraw
crossings (~20x/sec, like ``tqdm.n``) and once more at finish, so it stays a
plain attribute and no other code path pays any overhead. Any further bar
state -- ``previous_value`` in particular -- is maintained by the bar itself
inside its ``_fast_tick()``/``_fast_end()`` hooks (which route through
``update()``/``finish()``); ``bar.value`` is synced right before
``_fast_end()`` so ``finish()`` records the correct ``previous_value``.

The bar must implement the small protocol used below:
``_fast_begin()`` (start/draw 0%), ``_fast_tick(value)`` (redraw + recompute
``_next_update``), ``_fast_end()`` (finish), ``_fast_end_dirty()`` (finish
without completing, for early break/exception), plus the plain attributes
``value``, ``_next_update`` and ``_finished``.
"""


cdef class FastBarIterator:
    cdef object _it
    cdef object _bar
    cdef object _tick
    cdef Py_ssize_t _value
    cdef Py_ssize_t _next_update
    cdef bint _started
    cdef bint _first
    cdef bint _done

    def __cinit__(self, bar, iterable):
        self._it = iter(iterable)
        self._bar = bar
        self._tick = None
        self._value = 0
        self._next_update = 0
        self._started = False
        self._first = True
        self._done = False

    def __iter__(self):
        return self

    def __next__(self):
        cdef object item
        cdef Py_ssize_t v
        if not self._started:
            self._bar._fast_begin()
            self._tick = self._bar._fast_tick
            self._value = self._bar.value
            self._next_update = self._bar._next_update
            self._started = True
        try:
            item = next(self._it)
        except StopIteration:
            # Finish exactly once, like the generator fallback: repeated
            # next() on an exhausted iterator must not re-run finish().
            if not self._done:
                self._done = True
                self._bar.value = self._value  # sync final count
                self._bar._fast_end()
            raise
        if self._first:
            self._first = False
            return item
        v = self._value + 1
        self._value = v                       # C field only; no Python attr write
        if v >= self._next_update:
            self._tick(v)                     # update(): sets value + redraws
            self._next_update = self._bar._next_update
        return item

    def __dealloc__(self):
        # If iteration is abandoned (break/exception) before exhaustion, the
        # generator-based fallback would get a GeneratorExit and finish dirty,
        # restoring redirected streams (issue #212). A cdef iterator has no
        # such hook, so do the same teardown here. CPython refcounting fires
        # this promptly when the for-loop drops its reference after a break.
        cdef object bar = self._bar
        if self._started and not self._done and bar is not None:
            try:
                if not bar._finished:
                    bar.value = self._value
                    bar._fast_end_dirty()
            except BaseException:
                # Teardown only (possibly during interpreter shutdown); never
                # propagate. __dealloc__ exceptions are ignored regardless.
                pass
