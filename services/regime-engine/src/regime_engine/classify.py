"""Rule-based market regime classifier (brief Section 7).

Classifies into exactly one of the eight labels the brief names as a
minimum: BULLISH_TREND, BEARISH_TREND, SIDEWAYS, HIGH_VOLATILITY,
LOW_VOLATILITY, ACCUMULATION, DISTRIBUTION, STRESS_EVENT. Checked in a fixed
priority order (see `_classify` below) so exactly one label always wins.

This is deliberately rule-based (SMA spread for trend, rolling volatility
for vol level, OBV trend for accumulation/distribution, a return-vs-volatility
outlier check for stress), not a fitted probabilistic model (e.g. a Hidden
Markov Model, which brief Section 4's time-series list names). An HMM or
similar needs a fitting/training pipeline this repository doesn't have —
regime-engine's brief requirement is "probability/confidence, not only a
categorical label," which a calibrated *confidence heuristic* on top of
clear rules satisfies honestly, without pretending to be a statistically
fitted probability. `confidence` here means "how far past the triggering
threshold," not a model-calibrated probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from quant_core.returns import simple_returns
from quant_core.technical import obv as _obv
from quant_core.technical import sma as _sma
from quant_core.volatility import rolling_volatility as _rolling_volatility

from regime_engine.thresholds import RegimeThresholds

RegimeLabel = Literal[
    "BULLISH_TREND",
    "BEARISH_TREND",
    "SIDEWAYS",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "ACCUMULATION",
    "DISTRIBUTION",
    "STRESS_EVENT",
]

ALL_REGIME_LABELS: tuple[RegimeLabel, ...] = (
    "BULLISH_TREND",
    "BEARISH_TREND",
    "SIDEWAYS",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "ACCUMULATION",
    "DISTRIBUTION",
    "STRESS_EVENT",
)


class Bar(TypedDict):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class RegimeResult:
    label: RegimeLabel
    confidence: float
    metrics: dict[str, float]


def _threshold_confidence(value: float, threshold: float) -> float:
    """0.5 exactly at the threshold, 1.0 at 2x the threshold, 0.0 at value=0. Clamped to [0, 1]."""
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    return max(0.0, min(1.0, abs(value) / (2 * threshold)))


def classify_regime(bars: list[Bar], thresholds: RegimeThresholds | None = None) -> RegimeResult:
    thresholds = thresholds or RegimeThresholds()
    min_bars = max(
        thresholds.sma_slow_window, thresholds.volatility_window + 1, thresholds.obv_window
    )
    if len(bars) < min_bars:
        raise ValueError(f"need at least {min_bars} bars for the configured thresholds")

    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]

    sma_fast = _sma(closes, thresholds.sma_fast_window)[-1]
    sma_slow = _sma(closes, thresholds.sma_slow_window)[-1]
    trend_strength = (sma_fast - sma_slow) / sma_slow

    returns = simple_returns(closes[-(thresholds.volatility_window + 1) :])
    vol = _rolling_volatility(returns, thresholds.volatility_window)[-1]
    last_return = returns[-1]

    obv_window_closes = closes[-thresholds.obv_window :]
    obv_window_volumes = volumes[-thresholds.obv_window :]
    obv_series = _obv(obv_window_closes, obv_window_volumes)
    total_volume = sum(obv_window_volumes)
    obv_trend_ratio = (obv_series[-1] - obv_series[0]) / total_volume if total_volume > 0 else 0.0

    metrics = {
        "trend_strength": trend_strength,
        "volatility": vol,
        "last_return": last_return,
        "obv_trend_ratio": obv_trend_ratio,
    }

    return _classify(metrics, thresholds)


def _classify(metrics: dict[str, float], t: RegimeThresholds) -> RegimeResult:
    trend_strength = metrics["trend_strength"]
    vol = metrics["volatility"]
    last_return = metrics["last_return"]
    obv_trend_ratio = metrics["obv_trend_ratio"]

    if vol > 0 and abs(last_return) > t.stress_sigma * vol:
        confidence = _threshold_confidence(abs(last_return) / vol, 2 * t.stress_sigma)
        return RegimeResult("STRESS_EVENT", confidence, metrics)

    if abs(trend_strength) > t.trend_threshold:
        label: RegimeLabel = "BULLISH_TREND" if trend_strength > 0 else "BEARISH_TREND"
        confidence = _threshold_confidence(trend_strength, t.trend_threshold)
        return RegimeResult(label, confidence, metrics)

    if obv_trend_ratio > t.accumulation_obv_ratio:
        confidence = _threshold_confidence(obv_trend_ratio, t.accumulation_obv_ratio)
        return RegimeResult("ACCUMULATION", confidence, metrics)

    if obv_trend_ratio < -t.accumulation_obv_ratio:
        confidence = _threshold_confidence(obv_trend_ratio, t.accumulation_obv_ratio)
        return RegimeResult("DISTRIBUTION", confidence, metrics)

    if vol > t.high_volatility_threshold:
        confidence = _threshold_confidence(vol, t.high_volatility_threshold)
        return RegimeResult("HIGH_VOLATILITY", confidence, metrics)

    if vol < t.low_volatility_threshold:
        confidence = 1.0 - _threshold_confidence(vol, t.low_volatility_threshold)
        return RegimeResult("LOW_VOLATILITY", confidence, metrics)

    confidence = 1.0 - _threshold_confidence(trend_strength, t.trend_threshold)
    return RegimeResult("SIDEWAYS", confidence, metrics)
