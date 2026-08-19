"""Turns a window of OHLCV bars into a normalized feature vector using quant-core.

FEATURE_SET names this module's output so a later, incompatible feature set
can be added (e.g. "phase2-v2") without silently changing the meaning of
rows already in the `features` table (data/migrations/0003_features.sql).

Every feature that needs more bars than are available is set to None rather
than computed from a shorter, non-standard window — a None is honest about
"not enough history yet"; a value computed from the wrong window length
would silently mean something different from the same key on a later row.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from quant_core.returns import log_returns
from quant_core.stats import kurtosis, mean, skewness, std_dev
from quant_core.technical import bollinger_bands, ema, macd, obv, roc, rsi, sma, vwap
from quant_core.volatility import atr, realized_volatility, rolling_volatility

FEATURE_SET = "phase2-v1"
SCHEMA_VERSION = 1

# Phase 1 only ingests 1m bars; extended as new intervals are ingested.
_PERIODS_PER_YEAR_BY_INTERVAL = {
    "1m": 365 * 24 * 60,
    "1h": 365 * 24,
    "1d": 365,
}


class Bar(TypedDict):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def periods_per_year_for_interval(interval: str) -> float:
    try:
        return _PERIODS_PER_YEAR_BY_INTERVAL[interval]
    except KeyError as exc:
        raise ValueError(
            f"unknown interval {interval!r}; add it to _PERIODS_PER_YEAR_BY_INTERVAL"
        ) from exc


def _last_or_none(values: list[float] | None) -> float | None:
    return values[-1] if values else None


def _safe(fn, *args, **kwargs) -> float | None:  # noqa: ANN001, ANN002, ANN003
    """Runs `fn`; returns None instead of raising when there isn't enough history yet."""
    try:
        return fn(*args, **kwargs)
    except ValueError:
        return None


def compute_features(bars: Sequence[Bar], interval: str) -> dict[str, float | str | None]:
    """Computes the phase2-v1 feature vector for the most recent bar in `bars`.

    `bars` must be sorted ascending by timestamp and cover a single
    (symbol, interval) series. Returns a flat dict keyed by feature name;
    metadata keys (feature_set, timestamp) are included so callers can
    persist the row without re-deriving them.
    """
    if len(bars) == 0:
        raise ValueError("bars must be non-empty")

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b["volume"] for b in bars]

    log_rets = log_returns(closes) if len(closes) >= 2 else []
    periods_per_year = periods_per_year_for_interval(interval)

    features: dict[str, float | str | None] = {
        "feature_set": FEATURE_SET,
        "timestamp": bars[-1]["timestamp"],
        "last_close": closes[-1],
        "sma_20": _last_or_none(_safe(sma, closes, 20)),
        "ema_20": _last_or_none(_safe(ema, closes, 20)),
        "rsi_14": _last_or_none(_safe(rsi, closes, 14)),
        "roc_10": _last_or_none(_safe(roc, closes, 10)),
        "atr_14": _last_or_none(_safe(atr, highs, lows, closes, 14)),
        "obv": _last_or_none(_safe(obv, closes, volumes)),
        "vwap": _last_or_none(_safe(vwap, closes, volumes)),
        "mean_log_return": _safe(mean, log_rets),
        "std_log_return": _safe(std_dev, log_rets),
        "skewness_log_return": _safe(skewness, log_rets),
        "kurtosis_log_return": _safe(kurtosis, log_rets),
        "realized_vol_annualized": _safe(realized_volatility, log_rets, periods_per_year),
        "rolling_vol_20": _last_or_none(_safe(rolling_volatility, log_rets, 20)),
    }

    macd_result = _safe(macd, closes, 12, 26, 9)
    if macd_result is not None:
        macd_line, signal_line, histogram = macd_result
        features["macd_line"] = macd_line[-1]
        features["macd_signal"] = signal_line[-1]
        features["macd_histogram"] = histogram[-1]
    else:
        features["macd_line"] = None
        features["macd_signal"] = None
        features["macd_histogram"] = None

    bollinger = _safe(bollinger_bands, closes, 20, 2.0)
    if bollinger is not None:
        upper, middle, lower = bollinger[-1]
        features["bollinger_upper_20"] = upper
        features["bollinger_middle_20"] = middle
        features["bollinger_lower_20"] = lower
    else:
        features["bollinger_upper_20"] = None
        features["bollinger_middle_20"] = None
        features["bollinger_lower_20"] = None

    return features
