"""Backtest performance metrics (brief Section 14).

Drawdown and downside-deviation math is reused from
`quant_core.risk` rather than reimplemented — a backtest's equity curve and
a portfolio's equity curve are the same kind of object.

Deflated Sharpe Ratio (brief: "Deflated Sharpe or equivalent multiple-testing
adjustment") is substituted with a plain Bonferroni correction on a Sharpe
significance p-value (sharpe_significance_pvalue + bonferroni_adjusted_pvalue
below). The actual Deflated Sharpe Ratio formula (Bailey & Lopez de Prado)
has specific correction terms for skewness/kurtosis and the expected maximum
Sharpe ratio across N trials that are easy to misstate without a verified
reference implementation to check against — the same reason t-tests,
chi-square, and ADF/KPSS are deferred in quant_core/stats.py. Bonferroni is a
plainer, unambiguous, more conservative substitute that satisfies the
"or equivalent" clause honestly.

Capacity (how much capital a strategy can absorb before its own trading
moves the market) is not implemented: it needs a market-impact model, which
needs microstructure-engine (not implemented — see its README).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from quant_core.returns import annualized_return
from quant_core.risk import downside_deviation, max_drawdown


def sharpe_ratio(
    returns: Sequence[float], periods_per_year: float, risk_free_rate: float = 0.0
) -> float:
    """Annualized Sharpe ratio: mean(excess) / std_dev(excess) * sqrt(periods_per_year)."""
    if len(returns) < 2:
        raise ValueError("need at least two returns")
    excess = [r - risk_free_rate for r in returns]
    m = statistics.fmean(excess)
    sd = statistics.stdev(excess)
    if sd == 0:
        raise ValueError("std_dev of excess returns is zero; Sharpe ratio is undefined")
    return (m / sd) * math.sqrt(periods_per_year)


def sortino_ratio(
    returns: Sequence[float],
    periods_per_year: float,
    target: float = 0.0,
    risk_free_rate: float = 0.0,
) -> float:
    """Annualized Sortino ratio: mean(excess) / downside_deviation(returns, target) * sqrt(ppy)."""
    if len(returns) == 0:
        raise ValueError("returns must be non-empty")
    excess = [r - risk_free_rate for r in returns]
    m = statistics.fmean(excess)
    dd = downside_deviation(returns, target)
    if dd == 0:
        raise ValueError("downside deviation is zero; Sortino ratio is undefined")
    return (m / dd) * math.sqrt(periods_per_year)


def calmar_ratio(equity_curve: Sequence[float], periods_per_year: float) -> float:
    """Annualized return over maximum drawdown."""
    if len(equity_curve) < 2:
        raise ValueError("need at least two equity points")
    total_return = equity_curve[-1] / equity_curve[0] - 1
    ann_return = annualized_return(
        total_return, periods=len(equity_curve) - 1, periods_per_year=periods_per_year
    )
    mdd = max_drawdown(equity_curve)
    if mdd == 0:
        raise ValueError("max drawdown is zero; Calmar ratio is undefined")
    return ann_return / mdd


def recovery_factor(equity_curve: Sequence[float]) -> float:
    """Total return over maximum drawdown."""
    if len(equity_curve) < 2:
        raise ValueError("need at least two equity points")
    total_return = equity_curve[-1] / equity_curve[0] - 1
    mdd = max_drawdown(equity_curve)
    if mdd == 0:
        raise ValueError("max drawdown is zero; recovery factor is undefined")
    return total_return / mdd


def win_rate(trade_returns: Sequence[float]) -> float:
    if len(trade_returns) == 0:
        raise ValueError("trade_returns must be non-empty")
    return sum(1 for t in trade_returns if t > 0) / len(trade_returns)


def expectancy(trade_returns: Sequence[float]) -> float:
    """Mean return per trade."""
    if len(trade_returns) == 0:
        raise ValueError("trade_returns must be non-empty")
    return statistics.fmean(trade_returns)


def payoff_ratio(trade_returns: Sequence[float]) -> float:
    """Average winning trade return over average (absolute) losing trade return."""
    wins = [t for t in trade_returns if t > 0]
    losses = [t for t in trade_returns if t < 0]
    if not wins or not losses:
        raise ValueError("payoff_ratio needs at least one winning and one losing trade")
    return (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))


def profit_factor(trade_returns: Sequence[float]) -> float:
    """Sum of winning trade returns over sum of absolute losing trade returns."""
    gains = sum(t for t in trade_returns if t > 0)
    losses = sum(abs(t) for t in trade_returns if t < 0)
    if losses == 0:
        raise ValueError("no losing trades; profit factor is undefined (infinite)")
    return gains / losses


def turnover(positions: Sequence[float]) -> float:
    """Sum of absolute position changes over the backtest, including the initial entry from flat."""
    total = 0.0
    previous = 0.0
    for p in positions:
        total += abs(p - previous)
        previous = p
    return total


def sharpe_significance_pvalue(sharpe: float, num_periods: int) -> float:
    """Two-sided p-value for a Sharpe ratio under the null SR=0.

    Uses the standard asymptotic result SR_hat * sqrt(T) ~ N(0, 1) under the
    null hypothesis (i.i.d. returns; exact for normal returns, approximate
    otherwise). `sharpe` should be the *per-period* Sharpe ratio (not
    annualized) and `num_periods` the number of return observations it was
    computed from.
    """
    if num_periods < 2:
        raise ValueError("num_periods must be >= 2")
    z = sharpe * math.sqrt(num_periods)
    return 2 * (1 - statistics.NormalDist().cdf(abs(z)))


def bonferroni_adjusted_pvalue(p_value: float, num_trials: int) -> float:
    """Bonferroni multiple-testing correction: min(1, p_value * num_trials).

    See the module docstring for why this substitutes for the Deflated
    Sharpe Ratio here.
    """
    if not 0 <= p_value <= 1:
        raise ValueError("p_value must be between 0 and 1")
    if num_trials < 1:
        raise ValueError("num_trials must be >= 1")
    return min(1.0, p_value * num_trials)
