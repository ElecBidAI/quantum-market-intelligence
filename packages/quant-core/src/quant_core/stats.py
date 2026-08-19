"""Descriptive/inferential statistics (brief Section 4).

Implements the descriptive and correlation family in full. Formal hypothesis
tests that need a distribution CDF beyond the normal (t-tests, chi-square,
Kolmogorov-Smirnov) and econometric tests that need critical-value tables
(ADF/KPSS, Engle-Granger/Johansen cointegration) are deferred: implementing
them correctly without a numerics dependency (e.g. scipy, for the
incomplete beta/gamma functions and the ADF/KPSS/cointegration critical-value
tables) risks a subtly wrong p-value, which is worse than not offering the
test yet. They are picked up whenever the first regime/backtest consumer
actually needs them and a numerics dependency is deliberately added.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def mean(values: Sequence[float]) -> float:
    if len(values) == 0:
        raise ValueError("values must be non-empty")
    return statistics.fmean(values)


def median(values: Sequence[float]) -> float:
    if len(values) == 0:
        raise ValueError("values must be non-empty")
    return statistics.median(values)


def variance(values: Sequence[float]) -> float:
    """Sample variance (Bessel-corrected, ddof=1)."""
    if len(values) < 2:
        raise ValueError("need at least two values for sample variance")
    return statistics.variance(values)


def std_dev(values: Sequence[float]) -> float:
    """Sample standard deviation (Bessel-corrected, ddof=1)."""
    if len(values) < 2:
        raise ValueError("need at least two values for sample std_dev")
    return statistics.stdev(values)


def mad(values: Sequence[float]) -> float:
    """Mean absolute deviation from the mean."""
    if len(values) == 0:
        raise ValueError("values must be non-empty")
    m = statistics.fmean(values)
    return statistics.fmean(abs(v - m) for v in values)


def iqr(values: Sequence[float]) -> float:
    """Interquartile range (Q3 - Q1), via the same interpolation as transforms.percentile."""
    from quant_core.transforms import percentile as _percentile

    if len(values) == 0:
        raise ValueError("values must be non-empty")
    return _percentile(values, 75) - _percentile(values, 25)


def skewness(values: Sequence[float]) -> float:
    """Sample skewness (adjusted Fisher-Pearson standardized moment coefficient)."""
    n = len(values)
    if n < 3:
        raise ValueError("need at least three values for skewness")
    m = statistics.fmean(values)
    s = statistics.stdev(values)
    if s == 0:
        raise ValueError("std_dev is zero; skewness is undefined")
    m3 = sum((v - m) ** 3 for v in values) / n
    g1 = m3 / (s**3)
    return math.sqrt(n * (n - 1)) / (n - 2) * g1


def kurtosis(values: Sequence[float]) -> float:
    """Sample excess kurtosis (0 for a normal distribution)."""
    n = len(values)
    if n < 4:
        raise ValueError("need at least four values for kurtosis")
    m = statistics.fmean(values)
    s = statistics.stdev(values)
    if s == 0:
        raise ValueError("std_dev is zero; kurtosis is undefined")
    m4 = sum((v - m) ** 4 for v in values) / n
    g2 = m4 / (s**4) - 3
    return ((n - 1) / ((n - 2) * (n - 3))) * ((n + 1) * g2 + 6)


def covariance(x: Sequence[float], y: Sequence[float]) -> float:
    """Sample covariance (Bessel-corrected)."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    if len(x) < 2:
        raise ValueError("need at least two paired values for covariance")
    return statistics.covariance(x, y)


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson linear correlation coefficient, in [-1, 1]."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    if len(x) < 2:
        raise ValueError("need at least two paired values for correlation")
    sx = statistics.stdev(x)
    sy = statistics.stdev(y)
    if sx == 0 or sy == 0:
        raise ValueError("correlation is undefined when either series has zero variance")
    return statistics.covariance(x, y) / (sx * sy)


def _rank(values: Sequence[float]) -> list[float]:
    """Fractional (average) ranks, 1-indexed, with ties averaged."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average_rank = (i + j) / 2 + 1  # 1-indexed
        for k in range(i, j + 1):
            ranks[order[k]] = average_rank
        i = j + 1
    return ranks


def spearman_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman rank correlation: Pearson correlation of the ranks."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    if len(x) < 2:
        raise ValueError("need at least two paired values for correlation")
    return pearson_correlation(_rank(x), _rank(y))


def kendall_tau(x: Sequence[float], y: Sequence[float]) -> float:
    """Kendall's tau-a: (concordant - discordant) pairs over all pairs."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    n = len(x)
    if n < 2:
        raise ValueError("need at least two paired values for correlation")

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            dy = y[j] - y[i]
            sign = dx * dy
            if sign > 0:
                concordant += 1
            elif sign < 0:
                discordant += 1
    total_pairs = n * (n - 1) / 2
    return (concordant - discordant) / total_pairs


def rolling_correlation(x: Sequence[float], y: Sequence[float], window: int) -> list[float]:
    """Pearson correlation over each trailing window of length `window`."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(x) < window:
        raise ValueError("not enough values for the requested window")

    return [
        pearson_correlation(x[end - window : end], y[end - window : end])
        for end in range(window, len(x) + 1)
    ]


def autocorrelation(values: Sequence[float], lag: int) -> float:
    """Sample autocorrelation at the given lag: corr(values[:-lag], values[lag:])."""
    if lag < 1:
        raise ValueError("lag must be >= 1")
    if len(values) <= lag:
        raise ValueError("not enough values for the requested lag")
    return pearson_correlation(values[:-lag], values[lag:])


def confidence_interval_mean(
    values: Sequence[float], confidence: float = 0.95
) -> tuple[float, float]:
    """Normal-approximation confidence interval for the mean.

    Uses a z-critical value (statistics.NormalDist), not the exact Student-t
    distribution, so this is only a good approximation for reasonably large
    samples (rule of thumb: n >= 30). An exact t-interval is deferred along
    with the other distribution-CDF-dependent tests (see module docstring).
    """
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    n = len(values)
    if n < 2:
        raise ValueError("need at least two values for a confidence interval")

    m = statistics.fmean(values)
    se = statistics.stdev(values) / math.sqrt(n)
    z = statistics.NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    margin = z * se
    return (m - margin, m + margin)
