import pytest
from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds

from strategy_engine.strategies import TrendFollowingStrategy

THRESHOLDS = RegimeThresholds()


def make_bars(closes, volumes=None):
    if volumes is None:
        volumes = [100.0] * len(closes)
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def alt_noise(base, amp):
    return [c * (1 + amp * (1 if i % 2 == 0 else -1)) for i, c in enumerate(base)]


def test_generates_a_long_candidate_in_a_bullish_trend():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "BULLISH_TREND"

    candidate = TrendFollowingStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "LONG"
    assert candidate["strategyId"] == "trend_following_sma_v1"
    assert candidate["symbol"] == "BTC-USDT"
    assert candidate["venue"] == "binance"
    assert candidate["regime"] == "BULLISH_TREND"
    assert candidate["timestamp"] == bars[-1]["timestamp"]
    assert candidate["entryLogic"]["smaFast"] == pytest.approx(128.05559672107987)
    assert candidate["entryLogic"]["smaSlow"] == pytest.approx(119.08371123580821)
    assert candidate["stopLogic"]["stopPrice"] == pytest.approx(132.84470251933223)
    assert candidate["targetLogic"]["targetPrice"] == pytest.approx(136.5497897066365)
    assert candidate["expectedEdge"] == pytest.approx(0.07534099661628475)
    # stop must be below entry and target above entry for a LONG
    assert candidate["stopLogic"]["stopPrice"] < candidate["entryLogic"]["entryPrice"]
    assert candidate["targetLogic"]["targetPrice"] > candidate["entryLogic"]["entryPrice"]


def test_generates_a_short_candidate_in_a_bearish_trend():
    base = [100 * (0.995**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "BEARISH_TREND"

    candidate = TrendFollowingStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "SHORT"
    assert candidate["stopLogic"]["stopPrice"] > candidate["entryLogic"]["entryPrice"]
    assert candidate["targetLogic"]["targetPrice"] < candidate["entryLogic"]["entryPrice"]


def test_returns_none_in_a_regime_it_would_never_be_called_for():
    # even if somehow invoked directly (bypassing engine.run_strategies'
    # regime gate), a sideways regime should never produce a trend candidate.
    closes = alt_noise([100.0] * 60, 0.012)
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "SIDEWAYS"

    candidate = TrendFollowingStrategy().generate(bars, regime, "BTC-USDT", "binance")
    assert candidate is None
