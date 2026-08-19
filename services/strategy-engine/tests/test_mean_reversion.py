import pytest
from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds

from strategy_engine.strategies import MeanReversionStrategy

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


def test_generates_a_long_candidate_when_close_dips_below_the_lower_band():
    closes = alt_noise([100.0] * 59, 0.005)
    closes.append(closes[-1] * 0.97)  # a -3% dip on the final bar
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "SIDEWAYS"

    candidate = MeanReversionStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "LONG"
    assert candidate["strategyId"] == "mean_reversion_bollinger_v1"
    assert candidate["entryLogic"]["upperBand"] == pytest.approx(101.373849182829)
    assert candidate["entryLogic"]["lowerBand"] == pytest.approx(98.42465081717098)
    assert candidate["signalStrength"] == pytest.approx(0.3186122805819968)
    assert candidate["stopLogic"]["stopPrice"] == pytest.approx(96.95005163434197)
    assert candidate["targetLogic"]["targetPrice"] == pytest.approx(99.89925)
    assert candidate["expectedEdge"] == pytest.approx(0.024765348515156282)
    # for a LONG mean-reversion trade: stop below entry, target (mean) above entry
    entry = candidate["entryLogic"]["entryPrice"]
    assert candidate["stopLogic"]["stopPrice"] < entry < candidate["targetLogic"]["targetPrice"]


def test_generates_a_short_candidate_when_close_spikes_above_the_upper_band():
    closes = alt_noise([100.0] * 59, 0.005)
    closes.append(closes[-1] * 1.03)  # a +3% spike on the final bar
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "SIDEWAYS"

    candidate = MeanReversionStrategy().generate(bars, regime, "BTC-USDT", "binance")

    assert candidate is not None
    assert candidate["direction"] == "SHORT"
    entry = candidate["entryLogic"]["entryPrice"]
    assert candidate["targetLogic"]["targetPrice"] < entry < candidate["stopLogic"]["stopPrice"]


def test_no_candidate_when_close_is_inside_the_bands():
    closes = alt_noise([100.0] * 60, 0.002)
    bars = make_bars(closes)
    regime = classify_regime(bars, THRESHOLDS)
    candidate = MeanReversionStrategy().generate(bars, regime, "BTC-USDT", "binance")
    assert candidate is None
