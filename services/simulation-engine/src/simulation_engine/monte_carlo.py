"""Trade-sequence Monte Carlo (brief Section 13, brief Section 14 step 7).

Takes a set of historical/backtested trade returns (e.g.
`backtester.engine.BacktestResult.round_trip_trade_returns`) and
bootstrap-resamples many alternate trade sequences from them, then reports
the full output suite the brief asks for: PnL/terminal-equity distribution,
percentiles, probability of loss, probability of drawdown exceeding a
threshold, expected shortfall, recovery-time distribution, longest-loss-
streak distribution, and probability of ruin.

This resamples *trades*, not *bars* — the unit here is one already-realized
trade's return, not a return-per-bar. `quant_core.simulation` provides the
lower-level bar/price-path simulators (GBM, jump diffusion, etc.); this
module is specifically the "what if my historical trades had come in a
different order/mix" question.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from quant_core.risk import cvar as _cvar
from quant_core.risk import max_drawdown as _max_drawdown
from quant_core.simulation import iid_bootstrap_paths

DEFAULT_PERCENTILES = (1, 5, 25, 50, 75, 95, 99)


def bootstrap_trade_sequences(
    trade_returns: list[float], path_length: int, n_simulations: int, seed: int | None = None
) -> np.ndarray:
    """iid-bootstraps `n_simulations` alternate trade sequences of `path_length` trades each."""
    return iid_bootstrap_paths(trade_returns, path_length, n_simulations, seed=seed)


def terminal_multipliers(trade_sequences: np.ndarray) -> np.ndarray:
    """Compounded terminal equity multiplier for each simulated sequence: prod(1 + r)."""
    arr = np.asarray(trade_sequences, dtype=float)
    return np.prod(1 + arr, axis=1)


def equity_curves(trade_sequences: np.ndarray, initial_equity: float = 1.0) -> np.ndarray:
    """Full equity path per simulation, column 0 = initial_equity."""
    arr = np.asarray(trade_sequences, dtype=float)
    n_paths, path_length = arr.shape
    curves = np.empty((n_paths, path_length + 1))
    curves[:, 0] = initial_equity
    curves[:, 1:] = initial_equity * np.cumprod(1 + arr, axis=1)
    return curves


def percentiles(values: np.ndarray, ps: tuple[int, ...] = DEFAULT_PERCENTILES) -> dict[int, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise ValueError("values must be non-empty")
    return {p: float(np.percentile(arr, p)) for p in ps}


def probability_of_loss(multipliers: np.ndarray) -> float:
    """Fraction of simulations ending below their starting equity (multiplier < 1)."""
    arr = np.asarray(multipliers, dtype=float)
    if arr.size == 0:
        raise ValueError("multipliers must be non-empty")
    return float(np.mean(arr < 1.0))


def probability_of_drawdown_exceeding(curves: np.ndarray, threshold: float) -> float:
    """Fraction of simulated equity curves whose max drawdown exceeds `threshold`."""
    arr = np.asarray(curves, dtype=float)
    if arr.size == 0:
        raise ValueError("curves must be non-empty")
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    drawdowns = np.array([_max_drawdown(row.tolist()) for row in arr])
    return float(np.mean(drawdowns > threshold))


def expected_shortfall(terminal_returns: list[float], confidence: float = 0.95) -> float:
    """CVaR of the terminal-return distribution (quant_core.risk.cvar, reused not reimplemented)."""
    return _cvar(terminal_returns, confidence=confidence)


def probability_of_ruin(curves: np.ndarray, ruin_threshold: float) -> float:
    """Fraction of simulations whose equity ever drops below `ruin_threshold` of its start."""
    if not 0 < ruin_threshold < 1:
        raise ValueError("ruin_threshold must be between 0 and 1")
    arr = np.asarray(curves, dtype=float)
    if arr.size == 0:
        raise ValueError("curves must be non-empty")
    initial = arr[:, 0]
    breached = np.min(arr, axis=1) < ruin_threshold * initial
    return float(np.mean(breached))


def recovery_time_distribution(curves: np.ndarray) -> list[int | None]:
    """Periods from each path's worst drawdown's trough back to its prior peak.

    `None` means the path never recovered within the simulated horizon. A
    path with no drawdown at all reports 0 (trivially "already recovered").
    Only the single worst drawdown per path is measured, matching how
    `quant_core.risk.max_drawdown` defines "the" drawdown for a path.
    """
    arr = np.asarray(curves, dtype=float)
    result: list[int | None] = []
    for row in arr:
        running_peak = row[0]
        best_dd = 0.0
        best_peak_val = row[0]
        best_trough_idx: int | None = None
        for i, val in enumerate(row):
            if val > running_peak:
                running_peak = val
            dd = (running_peak - val) / running_peak
            if dd > best_dd:
                best_dd = dd
                best_peak_val = running_peak
                best_trough_idx = i

        if best_trough_idx is None:
            result.append(0)
            continue

        recovered_idx = next(
            (j for j in range(best_trough_idx, len(row)) if row[j] >= best_peak_val), None
        )
        result.append(None if recovered_idx is None else recovered_idx - best_trough_idx)
    return result


def longest_loss_streak_distribution(trade_sequences: np.ndarray) -> list[int]:
    """Longest run of consecutive losing trades (return < 0) within each simulated sequence."""
    arr = np.asarray(trade_sequences, dtype=float)
    result = []
    for row in arr:
        longest = 0
        current = 0
        for r in row:
            if r < 0:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        result.append(longest)
    return result


@dataclass(frozen=True)
class MonteCarloResult:
    terminal_multiplier_percentiles: dict[int, float]
    probability_of_loss: float
    probability_of_drawdown_exceeding_threshold: float
    drawdown_threshold: float
    expected_shortfall: float
    probability_of_ruin: float
    ruin_threshold: float
    recovery_times: list[int | None]
    longest_loss_streaks: list[int]
    n_simulations: int
    path_length: int


def run_trade_sequence_monte_carlo(
    trade_returns: list[float],
    path_length: int,
    n_simulations: int,
    drawdown_threshold: float = 0.20,
    ruin_threshold: float = 0.50,
    confidence: float = 0.95,
    seed: int | None = None,
) -> MonteCarloResult:
    """Runs the full trade-sequence Monte Carlo and reports every brief-Section-13 output."""
    sequences = bootstrap_trade_sequences(trade_returns, path_length, n_simulations, seed=seed)
    multipliers = terminal_multipliers(sequences)
    curves = equity_curves(sequences)
    terminal_returns = (multipliers - 1.0).tolist()

    return MonteCarloResult(
        terminal_multiplier_percentiles=percentiles(multipliers),
        probability_of_loss=probability_of_loss(multipliers),
        probability_of_drawdown_exceeding_threshold=probability_of_drawdown_exceeding(
            curves, drawdown_threshold
        ),
        drawdown_threshold=drawdown_threshold,
        expected_shortfall=expected_shortfall(terminal_returns, confidence=confidence),
        probability_of_ruin=probability_of_ruin(curves, ruin_threshold),
        ruin_threshold=ruin_threshold,
        recovery_times=recovery_time_distribution(curves),
        longest_loss_streaks=longest_loss_streak_distribution(sequences),
        n_simulations=n_simulations,
        path_length=path_length,
    )
