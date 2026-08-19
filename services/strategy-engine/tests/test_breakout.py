import pytest
from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds

from strategy_engine.strategies import BreakoutStrategy

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


def test_generates_a_long_candidate_on_an_upside_breakout():
    closes = alt_noise([100.0] * 59, 0.03)
    closes.append(closes[-1] * 1.1)  # a +10% breakout bar
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "HIGH_VOLATILITY"

    candidate = BreakoutStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "LONG"
    assert candidate["strategyId"] == "breakout_donchian_v1"
    assert candidate["entryLogic"]["channelUpper"] == pytest.approx(103.0)
    assert candidate["entryLogic"]["channelLower"] == pytest.approx(97.0)
    assert candidate["entryLogic"]["entryPrice"] == pytest.approx(113.30000000000001)
    assert candidate["stopLogic"]["stopPrice"] == pytest.approx(100.0)
    assert candidate["targetLogic"]["targetPrice"] == pytest.approx(119.30000000000001)
    assert candidate["expectedEdge"] == pytest.approx(0.052956751985878195)
    # a LONG breakout's stop (channel middle) must sit below the entry price
    assert candidate["stopLogic"]["stopPrice"] < candidate["entryLogic"]["entryPrice"]


def test_generates_a_short_candidate_on_a_downside_breakout():
    closes = alt_noise([100.0] * 59, 0.03)
    closes.append(closes[-1] * 0.9)  # a -10% breakdown bar
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "HIGH_VOLATILITY"

    candidate = BreakoutStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "SHORT"
    assert candidate["stopLogic"]["stopPrice"] > candidate["entryLogic"]["entryPrice"]


def test_uses_the_prior_channel_not_one_that_includes_the_current_bar():
    # a bar exactly at the (prior) channel boundary should not count as a breakout
    closes = alt_noise([100.0] * 59, 0.03)
    bars_at_boundary = make_bars([*closes, 103.0])  # equals the prior channel's upper bound exactly
    regime = classify_regime(bars_at_boundary, THRESHOLDS)
    candidate = BreakoutStrategy().generate(bars_at_boundary, regime, "BTC-USDT", "binance")
    assert candidate is None


def test_no_candidate_when_close_stays_inside_the_prior_channel():
    closes = alt_noise([100.0] * 60, 0.01)
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    candidate = BreakoutStrategy().generate(bars, regime, "BTC-USDT", "binance")
    assert candidate is None
