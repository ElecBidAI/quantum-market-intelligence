"""Risk measures and position sizing (brief Section 9).

Every function here reports risk; none of them decide APPROVE/REDUCE/REJECT
— that gating logic lives in services/risk-engine, which uses these as
inputs alongside hard, configurable limits. Keeping the math and the policy
in separate places means the policy can change without touching (or
re-testing) the math, and vice versa.

Risk of ruin is deferred to services/simulation-engine (brief Section 13
lists "probability of ruin" as a Monte Carlo *output*, not a closed-form
formula) — a trustworthy estimate needs a simulated trade-sequence
distribution, not a single formula, so it belongs with the Monte Carlo work
rather than being approximated here.

VaR/CVaR use a simple historical (order-statistic) convention: the loss at
the floor((1-confidence)*n)-th smallest return. This is a deliberate,
documented choice, not the only valid one — different conventions (linear
interpolation between order statistics, or a "nearest rank") give slightly
different numbers for small samples.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def _validate_returns(returns: Sequence[float], min_len: int = 1) -> None:
    if len(returns) < min_len:
        raise ValueError(f"need at least {min_len} return(s)")


def historical_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Historical (non-parametric) Value at Risk, as a positive loss fraction."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    _validate_returns(returns, min_len=2)
    ordered = sorted(returns)
    index = max(0, min(int((1 - confidence) * len(ordered)), len(ordered) - 1))
    return -ordered[index]


def parametric_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Parametric (Gaussian) Value at Risk, as a positive loss fraction."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    _validate_returns(returns, min_len=2)
    n = len(returns)
    m = sum(returns) / n
    variance = sum((r - m) ** 2 for r in returns) / (n - 1)
    sd = math.sqrt(variance)
    z = _inv_normal_cdf(confidence)
    return -(m - z * sd)


def _inv_normal_cdf(p: float) -> float:
    import statistics

    return statistics.NormalDist().inv_cdf(p)


def cvar(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Conditional VaR / Expected Shortfall: mean loss in the tail beyond the VaR cutoff."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    _validate_returns(returns, min_len=2)
    ordered = sorted(returns)
    cutoff = max(1, min(int((1 - confidence) * len(ordered)), len(ordered)))
    tail = ordered[:cutoff]
    return -sum(tail) / len(tail)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Maximum peak-to-trough drawdown, as a positive fraction of the peak."""
    _validate_returns(equity_curve, min_len=1)
    if equity_curve[0] <= 0:
        raise ValueError("equity_curve must start positive")

    peak = equity_curve[0]
    worst = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        worst = max(worst, (peak - e) / peak)
    return worst


def downside_deviation(returns: Sequence[float], target: float = 0.0) -> float:
    """Root-mean-square of returns below `target` (returns above target contribute zero)."""
    _validate_returns(returns, min_len=1)
    downside_sq = [min(0.0, r - target) ** 2 for r in returns]
    return math.sqrt(sum(downside_sq) / len(returns))


def ulcer_index(equity_curve: Sequence[float]) -> float:
    """RMS of percentage drawdowns from the running peak."""
    _validate_returns(equity_curve, min_len=1)
    if equity_curve[0] <= 0:
        raise ValueError("equity_curve must start positive")

    peak = equity_curve[0]
    squared_drawdowns = []
    for e in equity_curve:
        peak = max(peak, e)
        squared_drawdowns.append(((peak - e) / peak * 100) ** 2)
    return math.sqrt(sum(squared_drawdowns) / len(equity_curve))


def beta(asset_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
    """Beta of asset returns against benchmark returns: cov(asset, bench) / var(bench)."""
    if len(asset_returns) != len(benchmark_returns):
        raise ValueError("asset_returns and benchmark_returns must be the same length")
    n = len(asset_returns)
    if n < 2:
        raise ValueError("need at least two paired returns")

    ma = sum(asset_returns) / n
    mb = sum(benchmark_returns) / n
    cov = sum((asset_returns[i] - ma) * (benchmark_returns[i] - mb) for i in range(n)) / (n - 1)
    var_b = sum((b - mb) ** 2 for b in benchmark_returns) / (n - 1)
    if var_b == 0:
        raise ValueError("benchmark has zero variance; beta is undefined")
    return cov / var_b


def tracking_error(portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
    """Sample std_dev of (portfolio - benchmark) return differences."""
    if len(portfolio_returns) != len(benchmark_returns):
        raise ValueError("portfolio_returns and benchmark_returns must be the same length")
    n = len(portfolio_returns)
    if n < 2:
        raise ValueError("need at least two paired returns")

    diffs = [portfolio_returns[i] - benchmark_returns[i] for i in range(n)]
    m = sum(diffs) / n
    variance = sum((d - m) ** 2 for d in diffs) / (n - 1)
    return math.sqrt(variance)


def information_ratio(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float:
    """Mean active return over tracking error."""
    diffs = [p - b for p, b in zip(portfolio_returns, benchmark_returns, strict=True)]
    te = tracking_error(portfolio_returns, benchmark_returns)
    if te == 0:
        raise ValueError("tracking error is zero; information ratio is undefined")
    return (sum(diffs) / len(diffs)) / te


def omega_ratio(returns: Sequence[float], threshold: float = 0.0) -> float:
    """Sum of gains above `threshold` over sum of losses below it."""
    _validate_returns(returns, min_len=1)
    gains = sum(max(0.0, r - threshold) for r in returns)
    losses = sum(max(0.0, threshold - r) for r in returns)
    if losses == 0:
        raise ValueError("no returns below threshold; omega ratio is undefined (infinite)")
    return gains / losses


# --- Position sizing (brief Section 9, "Position sizing") ---------------------------------


def fixed_fractional_size(equity: float, risk_fraction: float, stop_distance: float) -> float:
    """Position size (in units of the asset) risking `risk_fraction` of equity to the stop."""
    if equity <= 0:
        raise ValueError("equity must be positive")
    if not 0 < risk_fraction <= 1:
        raise ValueError("risk_fraction must be in (0, 1]")
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")
    return (equity * risk_fraction) / stop_distance


def atr_based_size(
    equity: float, risk_fraction: float, atr: float, atr_multiplier: float = 2.0
) -> float:
    """Position size using `atr_multiplier * ATR` as the stop distance."""
    if atr <= 0:
        raise ValueError("atr must be positive")
    if atr_multiplier <= 0:
        raise ValueError("atr_multiplier must be positive")
    return fixed_fractional_size(equity, risk_fraction, atr * atr_multiplier)


def volatility_target_size(
    equity: float, target_volatility: float, asset_volatility: float
) -> float:
    """Notional exposure (in currency) that scales asset volatility down/up to a target."""
    if equity <= 0:
        raise ValueError("equity must be positive")
    if target_volatility <= 0:
        raise ValueError("target_volatility must be positive")
    if asset_volatility <= 0:
        raise ValueError("asset_volatility must be positive")
    return equity * (target_volatility / asset_volatility)


def fractional_kelly_size(
    win_probability: float, win_loss_ratio: float, fraction: float = 0.5
) -> float:
    """Fraction of equity to risk: `fraction` of the full Kelly criterion.

    Full Kelly f* = p - (1-p)/b, where p = win_probability and b = win_loss_ratio
    (average win / average loss). Clamped to [0, 1] — a negative or >1 full-Kelly
    result means the edge doesn't support sizing up at all, not a real position.
    """
    if not 0 < win_probability < 1:
        raise ValueError("win_probability must be in (0, 1)")
    if win_loss_ratio <= 0:
        raise ValueError("win_loss_ratio must be positive")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")

    full_kelly = win_probability - (1 - win_probability) / win_loss_ratio
    return max(0.0, min(1.0, full_kelly)) * fraction


# --- Exposure / concentration (brief Section 9, "Hard controls") --------------------------


def gross_exposure(weights: Sequence[float]) -> float:
    """Sum of absolute position weights (long + short), as a fraction of equity."""
    return sum(abs(w) for w in weights)


def net_exposure(weights: Sequence[float]) -> float:
    """Sum of signed position weights, as a fraction of equity."""
    return sum(weights)


def concentration_hhi(weights: Sequence[float]) -> float:
    """Herfindahl-Hirschman Index: sum(w_i^2); 1/n for equal weights, 1 for a single position."""
    if len(weights) == 0:
        raise ValueError("weights must be non-empty")
    gross = gross_exposure(weights)
    if gross == 0:
        return 0.0
    normalized = [abs(w) / gross for w in weights]
    return sum(w**2 for w in normalized)
