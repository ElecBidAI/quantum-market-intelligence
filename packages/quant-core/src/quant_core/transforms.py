"""Rolling/point transforms (brief Section 4, "Returns and transformations").

Completes the slice left open in returns.py: z-score, rolling normalization,
percentiles, winsorization, relative volume. All pure, all raise on invalid
input rather than imputing (see returns.py's module docstring for why).
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence


def z_score(value: float, mean: float, std_dev: float) -> float:
    """Standard score: (value - mean) / std_dev."""
    if std_dev <= 0:
        raise ValueError("std_dev must be positive")
    return (value - mean) / std_dev


def rolling_normalize(values: Sequence[float], window: int) -> list[float]:
    """Rolling z-score of each value against the trailing `window` (inclusive).

    The first `window - 1` points have no full window and are omitted, so the
    result has `len(values) - window + 1` entries — same convention as the
    other rolling_* functions in this package.
    """
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(values) < window:
        raise ValueError("not enough values for the requested window")

    result: list[float] = []
    for end in range(window, len(values) + 1):
        chunk = values[end - window : end]
        mean = statistics.fmean(chunk)
        std_dev = statistics.pstdev(chunk, mu=mean)
        if std_dev == 0:
            raise ValueError("std_dev is zero for a window; z-score is undefined")
        result.append((chunk[-1] - mean) / std_dev)
    return result


def percentile(values: Sequence[float], q: float) -> float:
    """`q`-th percentile (0-100) via linear interpolation between closest ranks."""
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    if len(values) == 0:
        raise ValueError("values must be non-empty")

    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    rank = (q / 100) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def winsorize(values: Sequence[float], limits: tuple[float, float] = (0.05, 0.05)) -> list[float]:
    """Clips the lowest/highest `limits` fraction of values to the nearest retained value.

    `limits` are fractions in [0, 0.5) for the (lower, upper) tails.
    """
    lower_limit, upper_limit = limits
    if not (0 <= lower_limit < 0.5) or not (0 <= upper_limit < 0.5):
        raise ValueError("limits must each be in [0, 0.5)")
    if len(values) == 0:
        raise ValueError("values must be non-empty")

    ordered = sorted(values)
    n = len(ordered)
    lower_index = int(n * lower_limit)
    upper_index = n - 1 - int(n * upper_limit)
    lower_bound = ordered[lower_index]
    upper_bound = ordered[upper_index]

    return [min(max(v, lower_bound), upper_bound) for v in values]


def relative_volume(volume: float, average_volume: float) -> float:
    """Ratio of current volume to a reference average volume (e.g. 20-bar average)."""
    if average_volume <= 0:
        raise ValueError("average_volume must be positive")
    return volume / average_volume
