"""Return/price-path simulators (brief Section 13, "Simulation Engine").

Every function takes an explicit `seed` and is otherwise pure — same seed,
same output, always (brief: "favor reproducibility over cleverness"). Random
number generation uses `numpy.random.default_rng`, not the legacy global
`numpy.random` state, so two calls never interfere with each other's
randomness even if one omits a seed.

These are path/return *generators* only. Turning a generated path or a
resampled trade sequence into risk outputs (percentiles, probability of
ruin, drawdown distributions, ...) is services/simulation-engine's job, not
this module's — same split as quant-core (formulas) vs. backtester/
risk-engine (decisions using those formulas).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def gbm_paths(
    s0: float,
    mu: float,
    sigma: float,
    dt: float,
    n_steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Geometric Brownian motion price paths via the exact log-Euler solution.

    Returns an array of shape (n_paths, n_steps + 1); column 0 is s0.
    """
    if s0 <= 0:
        raise ValueError("s0 must be positive")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_paths, n_steps))
    increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.cumsum(increments, axis=1)
    return s0 * np.exp(np.hstack([np.zeros((n_paths, 1)), log_paths]))


def jump_diffusion_paths(
    s0: float,
    mu: float,
    sigma: float,
    jump_intensity: float,
    jump_mean: float,
    jump_std: float,
    dt: float,
    n_steps: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Merton jump-diffusion price paths: GBM plus a compound-Poisson jump term.

    `jump_intensity` is the expected number of jumps per unit time; each
    jump's log-size is drawn from N(jump_mean, jump_std). Returns an array
    of shape (n_paths, n_steps + 1); column 0 is s0.
    """
    if s0 <= 0:
        raise ValueError("s0 must be positive")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if jump_intensity < 0:
        raise ValueError("jump_intensity must be non-negative")
    if jump_std < 0:
        raise ValueError("jump_std must be non-negative")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_paths, n_steps))
    diffusion = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z

    n_jumps = rng.poisson(jump_intensity * dt, size=(n_paths, n_steps))
    max_jumps = int(n_jumps.max()) if n_jumps.size else 0
    jump_sum = np.zeros((n_paths, n_steps))
    if max_jumps > 0:
        jump_sizes = rng.normal(jump_mean, jump_std, size=(n_paths, n_steps, max_jumps))
        mask = np.arange(max_jumps) < n_jumps[..., None]
        jump_sum = np.sum(jump_sizes * mask, axis=2)

    log_paths = np.cumsum(diffusion + jump_sum, axis=1)
    return s0 * np.exp(np.hstack([np.zeros((n_paths, 1)), log_paths]))


def student_t_returns(
    df: float, loc: float, scale: float, n: int, seed: int | None = None
) -> np.ndarray:
    """`n` i.i.d. returns from a Student-t (fatter tails than normal for finite df)."""
    if df <= 0:
        raise ValueError("df must be positive")
    if scale <= 0:
        raise ValueError("scale must be positive")
    if n < 1:
        raise ValueError("n must be >= 1")
    rng = np.random.default_rng(seed)
    return loc + scale * rng.standard_t(df, size=n)


def iid_bootstrap_paths(
    returns: Sequence[float], path_length: int, n_paths: int, seed: int | None = None
) -> np.ndarray:
    """Resamples `returns` with replacement into `n_paths` sequences of length `path_length`."""
    returns_arr = np.asarray(returns, dtype=float)
    if returns_arr.size == 0:
        raise ValueError("returns must be non-empty")
    if path_length < 1:
        raise ValueError("path_length must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(returns_arr), size=(n_paths, path_length))
    return returns_arr[idx]


def block_bootstrap_paths(
    returns: Sequence[float],
    block_size: int,
    path_length: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """Resamples contiguous blocks of `returns` (preserves within-block autocorrelation) into paths.

    Blocks are drawn with replacement and concatenated until at least
    `path_length` returns are assembled, then truncated to exactly
    `path_length`.
    """
    returns_arr = np.asarray(returns, dtype=float)
    n = len(returns_arr)
    if block_size < 1 or block_size > n:
        raise ValueError("block_size must be between 1 and len(returns)")
    if path_length < 1:
        raise ValueError("path_length must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")

    rng = np.random.default_rng(seed)
    n_blocks_needed = -(-path_length // block_size)  # ceil division
    max_start = n - block_size
    starts = rng.integers(0, max_start + 1, size=(n_paths, n_blocks_needed))

    paths = np.empty((n_paths, n_blocks_needed * block_size))
    for i in range(n_paths):
        segments = [returns_arr[s : s + block_size] for s in starts[i]]
        paths[i] = np.concatenate(segments)
    return paths[:, :path_length]


def regime_conditioned_bootstrap_paths(
    returns: Sequence[float],
    regime_labels: Sequence[object],
    target_regime: object,
    path_length: int,
    n_paths: int,
    seed: int | None = None,
) -> np.ndarray:
    """iid-bootstraps only from the returns whose aligned `regime_labels` equal `target_regime`.

    `regime_labels` must be caller-supplied and aligned index-for-index with
    `returns` — there is no live regime classifier to source these from yet
    (services/regime-engine, Phase 6); this function is regime-agnostic
    about where the labels came from.
    """
    returns_arr = np.asarray(returns, dtype=float)
    labels_arr = np.asarray(regime_labels, dtype=object)
    if len(returns_arr) != len(labels_arr):
        raise ValueError("returns and regime_labels must be the same length")

    mask = labels_arr == target_regime
    filtered = returns_arr[mask]
    if filtered.size == 0:
        raise ValueError(f"no returns found for regime {target_regime!r}")
    return iid_bootstrap_paths(filtered, path_length, n_paths, seed=seed)
