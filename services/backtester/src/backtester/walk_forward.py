"""Walk-forward window generation (brief Section 14, "Walk-forward testing").

Anchored-window (non-expanding) walk-forward: each window's train slice is a
fixed-size block immediately preceding its test slice, rolled forward by
`step` bars. An expanding-window variant (train slice grows over time
instead of sliding) is a reasonable alternative but isn't implemented —
add it if/when a consumer specifically needs it, rather than offering both
without a real caller for either.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def walk_forward_windows(
    bars: Sequence[T], train_size: int, test_size: int, step: int | None = None
) -> list[tuple[Sequence[T], Sequence[T]]]:
    if train_size < 1:
        raise ValueError("train_size must be >= 1")
    if test_size < 1:
        raise ValueError("test_size must be >= 1")
    step = test_size if step is None else step
    if step < 1:
        raise ValueError("step must be >= 1")

    windows: list[tuple[Sequence[T], Sequence[T]]] = []
    start = 0
    n = len(bars)
    while start + train_size + test_size <= n:
        train = bars[start : start + train_size]
        test = bars[start + train_size : start + train_size + test_size]
        windows.append((train, test))
        start += step
    return windows
