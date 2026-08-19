"""Configurable regime-classification thresholds.

Placeholder defaults, same caveat as risk_engine.limits.RiskLimits: not
researched or calibrated against real BTC/ETH history, just conservative
enough to make the classifier runnable and testable now. Whoever wires this
into a live pipeline must review and justify every value first — see
docs/risk/RISK-GOVERNANCE.md Section 5 ("weights must be configurable and
validated by strategy/regime").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeThresholds:
    # Fast/slow SMA relative spread beyond which price action counts as trending.
    sma_fast_window: int = 20
    sma_slow_window: int = 50
    trend_threshold: float = 0.02

    # Rolling volatility window and per-period thresholds (same units as the
    # input returns — e.g. per-bar, not annualized).
    volatility_window: int = 20
    high_volatility_threshold: float = 0.03
    low_volatility_threshold: float = 0.005

    # A single-bar return beyond stress_sigma * recent volatility is a stress event.
    stress_sigma: float = 4.0

    # OBV trend, normalized as (obv[-1] - obv[0]) / total_volume over the window,
    # beyond which net order flow counts as accumulation/distribution.
    obv_window: int = 20
    accumulation_obv_ratio: float = 0.3

    def __post_init__(self) -> None:
        if self.sma_fast_window < 1 or self.sma_slow_window < 1:
            raise ValueError("SMA windows must be >= 1")
        if self.sma_fast_window >= self.sma_slow_window:
            raise ValueError("sma_fast_window must be smaller than sma_slow_window")
        if self.trend_threshold <= 0:
            raise ValueError("trend_threshold must be positive")
        if self.volatility_window < 2:
            raise ValueError("volatility_window must be >= 2")
        if self.high_volatility_threshold <= self.low_volatility_threshold:
            raise ValueError("high_volatility_threshold must be greater than low_volatility")
        if self.low_volatility_threshold < 0:
            raise ValueError("low_volatility_threshold must be non-negative")
        if self.stress_sigma <= 0:
            raise ValueError("stress_sigma must be positive")
        if self.obv_window < 2:
            raise ValueError("obv_window must be >= 2")
        if not 0 < self.accumulation_obv_ratio <= 1:
            raise ValueError("accumulation_obv_ratio must be in (0, 1]")
