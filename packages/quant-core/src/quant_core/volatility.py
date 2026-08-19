"""Volatility estimators (brief Section 4, "Volatility").

GARCH/EGARCH are deferred: fitting either needs maximum-likelihood
optimization, which is a materially different (and easy to get subtly wrong)
piece of numerical code compared to the closed-form estimators below. They
are picked up once forecast-engine has a concrete need for a conditional
volatility model and a numerics dependency is deliberately added.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def rolling_volatility(returns: Sequence[float], window: int) -> list[float]:
    """Sample standard deviation of returns over each trailing window."""
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(returns) < window:
        raise ValueError("not enough returns for the requested window")

    result = []
    for end in range(window, len(returns) + 1):
        chunk = returns[end - window : end]
        m = sum(chunk) / window
        var = sum((r - m) ** 2 for r in chunk) / (window - 1)
        result.append(math.sqrt(var))
    return result


def realized_volatility(returns: Sequence[float], periods_per_year: float) -> float:
    """Annualized realized volatility from squared returns: sqrt(periods_per_year * mean(r^2))."""
    if len(returns) == 0:
        raise ValueError("returns must be non-empty")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    mean_sq = sum(r**2 for r in returns) / len(returns)
    return math.sqrt(periods_per_year * mean_sq)


def ewma_volatility(returns: Sequence[float], lambda_: float = 0.94) -> float:
    """RiskMetrics-style EWMA volatility (latest estimate only).

    variance_0 = returns[0]^2; variance_t = lambda*variance_{t-1} + (1-lambda)*r_t^2.
    """
    if not 0 < lambda_ < 1:
        raise ValueError("lambda_ must be between 0 and 1")
    if len(returns) == 0:
        raise ValueError("returns must be non-empty")

    variance = returns[0] ** 2
    for r in returns[1:]:
        variance = lambda_ * variance + (1 - lambda_) * r**2
    return math.sqrt(variance)


def _check_ohlc_lengths(*series: Sequence[float]) -> None:
    lengths = {len(s) for s in series}
    if len(lengths) != 1:
        raise ValueError("all OHLC series must be the same length")
    if lengths == {0}:
        raise ValueError("series must be non-empty")


def parkinson_volatility(
    highs: Sequence[float], lows: Sequence[float], periods_per_year: float
) -> float:
    """Parkinson (1980) high-low range volatility estimator, annualized."""
    _check_ohlc_lengths(highs, lows)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    n = len(highs)
    total = sum(math.log(hi / lo) ** 2 for hi, lo in zip(highs, lows, strict=True))
    variance = total / n / (4 * math.log(2))
    return math.sqrt(periods_per_year * variance)


def garman_klass_volatility(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    periods_per_year: float,
) -> float:
    """Garman-Klass (1980) OHLC volatility estimator, annualized."""
    _check_ohlc_lengths(opens, highs, lows, closes)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    n = len(opens)
    total = 0.0
    for op, hi, lo, cl in zip(opens, highs, lows, closes, strict=True):
        total += 0.5 * math.log(hi / lo) ** 2 - (2 * math.log(2) - 1) * math.log(cl / op) ** 2
    variance = total / n
    return math.sqrt(periods_per_year * variance)


def rogers_satchell_volatility(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    periods_per_year: float,
) -> float:
    """Rogers-Satchell (1991) OHLC volatility estimator (drift-independent), annualized."""
    _check_ohlc_lengths(opens, highs, lows, closes)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    n = len(opens)
    total = 0.0
    for op, hi, lo, cl in zip(opens, highs, lows, closes, strict=True):
        total += math.log(hi / cl) * math.log(hi / op) + math.log(lo / cl) * math.log(lo / op)
    variance = total / n
    return math.sqrt(periods_per_year * variance)


def atr(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], window: int
) -> list[float]:
    """Average True Range with Wilder smoothing.

    The first output is the simple average of the first `window` true
    ranges; each subsequent value is Wilder-smoothed: ATR_t = (ATR_{t-1} *
    (window-1) + TR_t) / window.
    """
    _check_ohlc_lengths(highs, lows, closes)
    if window < 1:
        raise ValueError("window must be >= 1")
    n = len(closes)
    if n < window + 1:
        raise ValueError("not enough bars for the requested window (need window+1 closes)")

    true_ranges = []
    for i in range(1, n):
        hi, lo, prev_close = highs[i], lows[i], closes[i - 1]
        true_ranges.append(max(hi - lo, abs(hi - prev_close), abs(lo - prev_close)))

    result = [sum(true_ranges[:window]) / window]
    for tr in true_ranges[window:]:
        result.append((result[-1] * (window - 1) + tr) / window)
    return result
