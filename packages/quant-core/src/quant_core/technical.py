"""Technical/momentum indicators (brief Section 4, "Technical/momentum").

Hurst exponent is deferred: a trustworthy estimator needs validation against
a reference implementation across multiple regimes (random walk, trending,
mean-reverting) to be confident it's not subtly biased, which is a bigger
validation effort than the closed-form indicators below. It is picked up
once regime-engine has a concrete use for it.

All rolling functions follow the same convention as volatility.py /
stats.py: the output has `len(input) - window + 1` entries (or fewer, for
functions that also need a prior bar, like ATR/ADX).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from quant_core.volatility import atr as _atr


def sma(prices: Sequence[float], window: int) -> list[float]:
    """Simple moving average."""
    if window < 1:
        raise ValueError("window must be >= 1")
    if len(prices) < window:
        raise ValueError("not enough prices for the requested window")
    return [sum(prices[i - window : i]) / window for i in range(window, len(prices) + 1)]


def ema(prices: Sequence[float], window: int) -> list[float]:
    """Exponential moving average, seeded by the SMA of the first `window` prices."""
    if window < 1:
        raise ValueError("window must be >= 1")
    if len(prices) < window:
        raise ValueError("not enough prices for the requested window")

    alpha = 2 / (window + 1)
    result = [sum(prices[:window]) / window]
    for price in prices[window:]:
        result.append(price * alpha + result[-1] * (1 - alpha))
    return result


def rsi(prices: Sequence[float], window: int = 14) -> list[float]:
    """Wilder's Relative Strength Index, in [0, 100]."""
    if window < 1:
        raise ValueError("window must be >= 1")
    if len(prices) < window + 1:
        raise ValueError("not enough prices for the requested window (need window+1 prices)")

    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(c, 0.0) for c in changes]
    losses = [max(-c, 0.0) for c in changes]

    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window

    def to_rsi(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0
        return 100 - 100 / (1 + gain / loss)

    result = [to_rsi(avg_gain, avg_loss)]
    for gain, loss in zip(gains[window:], losses[window:], strict=True):
        avg_gain = (avg_gain * (window - 1) + gain) / window
        avg_loss = (avg_loss * (window - 1) + loss) / window
        result.append(to_rsi(avg_gain, avg_loss))
    return result


def macd(
    prices: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float], list[float], list[float]]:
    """MACD line, signal line, and histogram (macd - signal)."""
    if fast >= slow:
        raise ValueError("fast window must be smaller than slow window")

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    # slow EMA starts later; align both series on the slow EMA's timeline
    offset = len(ema_fast) - len(ema_slow)
    macd_line = [ema_fast[i + offset] - ema_slow[i] for i in range(len(ema_slow))]
    if len(macd_line) < signal:
        raise ValueError("not enough data to compute the signal line")
    signal_line = ema(macd_line, signal)
    histogram_offset = len(macd_line) - len(signal_line)
    histogram = [macd_line[i + histogram_offset] - signal_line[i] for i in range(len(signal_line))]
    return macd_line, signal_line, histogram


def bollinger_bands(
    prices: Sequence[float], window: int = 20, num_std: float = 2.0
) -> list[tuple[float, float, float]]:
    """(upper, middle, lower) bands using the population std_dev within each window."""
    if window < 2:
        raise ValueError("window must be >= 2")
    if len(prices) < window:
        raise ValueError("not enough prices for the requested window")

    result = []
    for end in range(window, len(prices) + 1):
        chunk = prices[end - window : end]
        m = sum(chunk) / window
        variance = sum((p - m) ** 2 for p in chunk) / window
        sd = math.sqrt(variance)
        result.append((m + num_std * sd, m, m - num_std * sd))
    return result


def roc(prices: Sequence[float], window: int) -> list[float]:
    """Rate of change (%) versus the price `window` bars ago."""
    if window < 1:
        raise ValueError("window must be >= 1")
    if len(prices) <= window:
        raise ValueError("not enough prices for the requested window")
    return [
        (prices[i] - prices[i - window]) / prices[i - window] * 100
        for i in range(window, len(prices))
    ]


def vwap(prices: Sequence[float], volumes: Sequence[float]) -> list[float]:
    """Cumulative volume-weighted average price from the start of the series."""
    if len(prices) != len(volumes):
        raise ValueError("prices and volumes must be the same length")
    if len(prices) == 0:
        raise ValueError("prices must be non-empty")

    result = []
    cumulative_pv = 0.0
    cumulative_v = 0.0
    for price, volume in zip(prices, volumes, strict=True):
        cumulative_pv += price * volume
        cumulative_v += volume
        if cumulative_v == 0:
            raise ValueError("cumulative volume is zero; VWAP is undefined")
        result.append(cumulative_pv / cumulative_v)
    return result


def obv(closes: Sequence[float], volumes: Sequence[float]) -> list[float]:
    """On-Balance Volume: running sum of +/-volume based on the close's direction."""
    if len(closes) != len(volumes):
        raise ValueError("closes and volumes must be the same length")
    if len(closes) == 0:
        raise ValueError("closes must be non-empty")

    result = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


def donchian_channel(
    highs: Sequence[float], lows: Sequence[float], window: int
) -> list[tuple[float, float, float]]:
    """Donchian channel (upper, middle, lower) over the window: highest high / avg / lowest low."""
    if len(highs) != len(lows):
        raise ValueError("highs and lows must be the same length")
    if window < 1:
        raise ValueError("window must be >= 1")
    if len(highs) < window:
        raise ValueError("not enough bars for the requested window")

    result = []
    for end in range(window, len(highs) + 1):
        hi = max(highs[end - window : end])
        lo = min(lows[end - window : end])
        result.append((hi, (hi + lo) / 2, lo))
    return result


def keltner_channel(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    window: int,
    atr_multiplier: float = 2.0,
) -> list[tuple[float, float, float]]:
    """(upper, middle, lower) Keltner channel: EMA(close) +/- atr_multiplier * ATR."""
    ema_line = ema(closes, window)
    atr_line = _atr(highs, lows, closes, window)
    n = min(len(ema_line), len(atr_line))
    ema_line = ema_line[-n:]
    atr_line = atr_line[-n:]
    return [
        (e + atr_multiplier * a, e, e - atr_multiplier * a)
        for e, a in zip(ema_line, atr_line, strict=True)
    ]


def _wilder_smooth(values: Sequence[float], window: int) -> list[float]:
    result = [sum(values[:window])]
    for v in values[window:]:
        result.append(result[-1] - result[-1] / window + v)
    return result


def adx(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], window: int = 14
) -> list[float]:
    """Average Directional Index (trend strength, 0-100, direction-agnostic)."""
    if len(highs) != len(lows) or len(highs) != len(closes):
        raise ValueError("highs, lows, and closes must be the same length")
    if window < 1:
        raise ValueError("window must be >= 1")
    n = len(closes)
    if n < 2 * window + 1:
        raise ValueError("not enough bars for the requested window (need at least 2*window+1)")

    plus_dm = []
    minus_dm = []
    true_ranges = []
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        hi, lo, prev_close = highs[i], lows[i], closes[i - 1]
        true_ranges.append(max(hi - lo, abs(hi - prev_close), abs(lo - prev_close)))

    smoothed_tr = _wilder_smooth(true_ranges, window)
    smoothed_plus_dm = _wilder_smooth(plus_dm, window)
    smoothed_minus_dm = _wilder_smooth(minus_dm, window)

    tr_pairs = list(zip(smoothed_plus_dm, smoothed_minus_dm, smoothed_tr, strict=True))
    plus_di = [100 * pdm / t if t != 0 else 0.0 for pdm, _mdm, t in tr_pairs]
    minus_di = [100 * mdm / t if t != 0 else 0.0 for _pdm, mdm, t in tr_pairs]
    dx = [
        100 * abs(p - m) / (p + m) if (p + m) != 0 else 0.0
        for p, m in zip(plus_di, minus_di, strict=True)
    ]

    result = [sum(dx[:window]) / window]
    for d in dx[window:]:
        result.append((result[-1] * (window - 1) + d) / window)
    return result


def spread_zscore(spread: Sequence[float], window: int) -> list[float]:
    """Rolling z-score of a spread series (e.g. pairs trading).

    Delegates to transforms.rolling_normalize.
    """
    from quant_core.transforms import rolling_normalize

    return rolling_normalize(spread, window)
