"""Portfolio allocation (brief Section 10).

Needs matrix algebra (covariance-matrix inversion), so this is the one
quant-core module with a dependency: numpy. That's a deliberate exception to
the rest of the package's zero-dependency stance — numpy is a foundational,
extremely well-vetted numerical library (unlike e.g. scipy's statistical
distribution/optimization routines, which quant-core's other modules
deliberately avoid depending on for correctness-risk reasons documented in
stats.py/volatility.py).

min_variance_weights and max_sharpe_weights are the *unconstrained* (can go
short, can exceed 100% via leverage) closed-form solutions. Long-only /
turnover / transaction-cost-constrained optimization needs a quadratic
program, which needs a QP solver — deferred until a portfolio-engine
consumer actually needs constrained optimization, per the "don't add a
numerics dependency speculatively" stance above.

Black-Litterman and Hierarchical Risk Parity are deferred for the same
reason as GARCH/cointegration in the other modules: both are materially
more involved (Black-Litterman needs a view/uncertainty specification and a
prior; HRP needs hierarchical clustering and quasi-diagonalization) than
what's implemented here, and a half-correct implementation of either is
worse than not offering it yet.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def expected_return(weights: Sequence[float], mu: Sequence[float]) -> float:
    """Portfolio expected return: E[Rp] = w'mu."""
    w = np.asarray(weights, dtype=float)
    m = np.asarray(mu, dtype=float)
    _check_same_length(w, m)
    return float(w @ m)


def variance(weights: Sequence[float], covariance: Sequence[Sequence[float]]) -> float:
    """Portfolio variance: sigma_p^2 = w'*Sigma*w."""
    w = np.asarray(weights, dtype=float)
    cov = _check_covariance(covariance, len(w))
    return float(w @ cov @ w)


def volatility(weights: Sequence[float], covariance: Sequence[Sequence[float]]) -> float:
    """Portfolio volatility: sqrt(w'*Sigma*w)."""
    return float(np.sqrt(variance(weights, covariance)))


def min_variance_weights(covariance: Sequence[Sequence[float]]) -> list[float]:
    """Unconstrained global minimum-variance weights: (Sigma^-1 1) / (1' Sigma^-1 1)."""
    cov = np.asarray(covariance, dtype=float)
    _check_square(cov)
    ones = np.ones(cov.shape[0])
    inv = np.linalg.inv(cov)
    raw = inv @ ones
    return (raw / (ones @ raw)).tolist()


def max_sharpe_weights(
    mu: Sequence[float], covariance: Sequence[Sequence[float]], risk_free_rate: float = 0.0
) -> list[float]:
    """Unconstrained tangency (max-Sharpe) weights: proportional to Sigma^-1 (mu - rf*1)."""
    m = np.asarray(mu, dtype=float)
    cov = _check_covariance(covariance, len(m))
    ones = np.ones(len(m))
    excess = m - risk_free_rate * ones
    inv = np.linalg.inv(cov)
    raw = inv @ excess
    total = raw.sum()
    if total == 0:
        raise ValueError("tangency weights sum to zero; max-Sharpe portfolio is undefined")
    return (raw / total).tolist()


def diversification_ratio(
    weights: Sequence[float], covariance: Sequence[Sequence[float]]
) -> float:
    """Weighted average of individual vols over portfolio vol (>=1 unless perfectly correlated)."""
    w = np.asarray(weights, dtype=float)
    cov = _check_covariance(covariance, len(w))
    individual_vols = np.sqrt(np.diag(cov))
    port_vol = float(np.sqrt(w @ cov @ w))
    if port_vol == 0:
        raise ValueError("portfolio volatility is zero; diversification ratio is undefined")
    return float(w @ individual_vols) / port_vol


def marginal_risk_contribution(
    weights: Sequence[float], covariance: Sequence[Sequence[float]]
) -> list[float]:
    """d(portfolio_vol)/d(w_i) = (Sigma w)_i / portfolio_vol."""
    w = np.asarray(weights, dtype=float)
    cov = _check_covariance(covariance, len(w))
    port_vol = float(np.sqrt(w @ cov @ w))
    if port_vol == 0:
        raise ValueError("portfolio volatility is zero; marginal risk contribution is undefined")
    return ((cov @ w) / port_vol).tolist()


def component_risk_contribution(
    weights: Sequence[float], covariance: Sequence[Sequence[float]]
) -> list[float]:
    """w_i * marginal_risk_contribution_i; sums to portfolio volatility."""
    w = np.asarray(weights, dtype=float)
    mrc = np.asarray(marginal_risk_contribution(weights, covariance))
    return (w * mrc).tolist()


def risk_parity_weights(
    covariance: Sequence[Sequence[float]], max_iter: int = 1000, tol: float = 1e-10
) -> list[float]:
    """Equal-risk-contribution weights via iterative proportional scaling.

    Starts from equal weights and repeatedly rescales each weight by
    (target_contribution / actual_contribution), renormalizing to sum to 1.
    This is a simple, well-behaved fixed-point iteration for the long-only
    risk-parity problem — not the only algorithm (Newton-based solvers
    converge faster) but easy to verify: check the output's own component
    risk contributions are equal, rather than trusting the iteration alone.
    """
    cov = np.asarray(covariance, dtype=float)
    _check_square(cov)
    n = cov.shape[0]
    w = np.ones(n) / n

    for _ in range(max_iter):
        port_vol = np.sqrt(w @ cov @ w)
        if port_vol == 0:
            raise ValueError("portfolio volatility is zero; risk parity is undefined")
        contributions = w * (cov @ w) / port_vol
        target = port_vol / n
        new_w = w * (target / contributions)
        new_w = new_w / new_w.sum()
        if np.max(np.abs(new_w - w)) < tol:
            return new_w.tolist()
        w = new_w
    return w.tolist()


def _check_same_length(a: np.ndarray, b: np.ndarray) -> None:
    if a.shape[0] != b.shape[0]:
        raise ValueError("weights and mu must be the same length")


def _check_square(cov: np.ndarray) -> None:
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError("covariance must be a square matrix")


def _check_covariance(covariance: Sequence[Sequence[float]], n: int) -> np.ndarray:
    cov = np.asarray(covariance, dtype=float)
    _check_square(cov)
    if cov.shape[0] != n:
        raise ValueError("covariance dimensions must match the number of weights")
    return cov
