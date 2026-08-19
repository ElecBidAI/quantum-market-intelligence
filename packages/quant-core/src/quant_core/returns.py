"""Return calculations (brief Section 4, "Returns and transformations").

Phase 0 implements only this first slice of quant-core (simple/log/cumulative/
annualized return) as the minimum tested foundation. The remaining formulas in
that section (z-score, rolling normalization, percentiles, winsorization,
relative volume) and the other quant-core sections (statistics, probability,
time series, volatility, technical/momentum) are implemented starting Phase 2,
alongside their consumers in feature-engine/statistical-engine, so schema and
usage land together instead of a formula library growing ahead of any caller.

All functions are pure and raise on invalid input rather than silently
imputing a value, matching the "never silently impute" rule in
docs/architecture/DATA-CONTRACTS.md.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def simple_return(price_start: float, price_end: float) -> float:
    """Simple return: r_t = P_t / P_(t-1) - 1."""
    if price_start == 0:
        raise ValueError("price_start must be non-zero")
    return price_end / price_start - 1


def log_return(price_start: float, price_end: float) -> float:
    """Log return: g_t = ln(P_t / P_(t-1))."""
    if price_start <= 0 or price_end <= 0:
        raise ValueError("prices must be positive for a log return")
    return math.log(price_end / price_start)


def simple_returns(prices: Sequence[float]) -> list[float]:
    """Simple returns for each consecutive pair in `prices`."""
    if len(prices) < 2:
        raise ValueError("need at least two prices to compute a return")
    return [simple_return(prices[i - 1], prices[i]) for i in range(1, len(prices))]


def log_returns(prices: Sequence[float]) -> list[float]:
    """Log returns for each consecutive pair in `prices`."""
    if len(prices) < 2:
        raise ValueError("need at least two prices to compute a return")
    return [log_return(prices[i - 1], prices[i]) for i in range(1, len(prices))]


def cumulative_return(returns: Sequence[float]) -> float:
    """Cumulative return from a sequence of simple per-period returns.

    Compounds as prod(1 + r_i) - 1, not a naive sum.
    """
    if len(returns) == 0:
        raise ValueError("returns must be non-empty")
    total = 1.0
    for r in returns:
        total *= 1 + r
    return total - 1


def annualized_return(total_return: float, periods: float, periods_per_year: float) -> float:
    """Annualizes a total return observed over `periods` periods.

    `periods` and `periods_per_year` must use the same unit (e.g. both in
    trading days, or both in hours).
    """
    if periods <= 0:
        raise ValueError("periods must be positive")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    growth = 1 + total_return
    if growth < 0:
        raise ValueError("total_return implies a negative growth factor (< -100%)")
    return growth ** (periods_per_year / periods) - 1
