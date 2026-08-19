import pytest

from regime_engine.classify import ALL_REGIME_LABELS, classify_regime
from regime_engine.thresholds import RegimeThresholds

THRESHOLDS = RegimeThresholds()


def make_bars(closes, volumes=None):
    if volumes is None:
        volumes = [100.0] * len(closes)
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def alt_noise(base, amp):
    """Alternating +/- amp noise — keeps a series from having exactly-zero volatility
    (a perfectly smooth synthetic trend has zero variance, which is unrealistic and
    triggers a spurious STRESS_EVENT via division by a near-zero volatility)."""
    return [c * (1 + amp * (1 if i % 2 == 0 else -1)) for i, c in enumerate(base)]


def test_all_regime_labels_is_exactly_the_briefs_minimum_set():
    assert set(ALL_REGIME_LABELS) == {
        "BULLISH_TREND",
        "BEARISH_TREND",
        "SIDEWAYS",
        "HIGH_VOLATILITY",
        "LOW_VOLATILITY",
        "ACCUMULATION",
        "DISTRIBUTION",
        "STRESS_EVENT",
    }


def test_rejects_too_few_bars():
    with pytest.raises(ValueError):
        classify_regime(make_bars([100.0] * 10), THRESHOLDS)


class TestEachRegimeLabel:
    def test_bullish_trend(self):
        base = [100 * (1.005**i) for i in range(60)]
        result = classify_regime(make_bars(alt_noise(base, 0.001)), THRESHOLDS)
        assert result.label == "BULLISH_TREND"
        assert result.metrics["trend_strength"] > 0
        assert 0.0 <= result.confidence <= 1.0

    def test_bearish_trend(self):
        base = [100 * (0.995**i) for i in range(60)]
        result = classify_regime(make_bars(alt_noise(base, 0.001)), THRESHOLDS)
        assert result.label == "BEARISH_TREND"
        assert result.metrics["trend_strength"] < 0

    def test_sideways(self):
        closes = alt_noise([100.0] * 60, 0.012)
        result = classify_regime(make_bars(closes), THRESHOLDS)
        assert result.label == "SIDEWAYS"

    def test_high_volatility(self):
        closes = alt_noise([100.0] * 60, 0.03)
        result = classify_regime(make_bars(closes), THRESHOLDS)
        assert result.label == "HIGH_VOLATILITY"
        assert result.metrics["volatility"] > THRESHOLDS.high_volatility_threshold

    def test_low_volatility(self):
        closes = alt_noise([100.0] * 60, 0.001)
        result = classify_regime(make_bars(closes), THRESHOLDS)
        assert result.label == "LOW_VOLATILITY"
        assert result.metrics["volatility"] < THRESHOLDS.low_volatility_threshold

    def test_accumulation(self):
        closes = alt_noise([100.0] * 60, 0.003)
        volumes = [100.0] + [
            300.0 if closes[i] > closes[i - 1] else 50.0 for i in range(1, 60)
        ]
        result = classify_regime(make_bars(closes, volumes), THRESHOLDS)
        assert result.label == "ACCUMULATION"
        assert result.metrics["obv_trend_ratio"] > THRESHOLDS.accumulation_obv_ratio

    def test_distribution(self):
        closes = alt_noise([100.0] * 60, 0.003)
        volumes = [100.0] + [
            50.0 if closes[i] > closes[i - 1] else 300.0 for i in range(1, 60)
        ]
        result = classify_regime(make_bars(closes, volumes), THRESHOLDS)
        assert result.label == "DISTRIBUTION"
        assert result.metrics["obv_trend_ratio"] < -THRESHOLDS.accumulation_obv_ratio

    def test_stress_event(self):
        closes = alt_noise([100.0] * 59, 0.002)
        closes.append(closes[-1] * 0.85)  # a -15% single-bar crash
        result = classify_regime(make_bars(closes), THRESHOLDS)
        assert result.label == "STRESS_EVENT"
        assert result.metrics["last_return"] < -0.1


def test_stress_event_takes_priority_over_a_simultaneous_trend():
    # a steep uptrend that also ends in a crash bar must still be flagged STRESS_EVENT,
    # not BULLISH_TREND — stress is checked first in the priority order.
    base = [100 * (1.01**i) for i in range(59)]
    closes = alt_noise(base, 0.001)
    closes.append(closes[-1] * 0.7)  # a -30% crash on top of the uptrend
    result = classify_regime(make_bars(closes), THRESHOLDS)
    assert result.label == "STRESS_EVENT"


def test_confidence_is_always_in_zero_one_range():
    scenarios = [
        alt_noise([100 * (1.005**i) for i in range(60)], 0.001),
        alt_noise([100.0] * 60, 0.012),
        alt_noise([100.0] * 60, 0.001),
    ]
    for closes in scenarios:
        result = classify_regime(make_bars(closes), THRESHOLDS)
        assert 0.0 <= result.confidence <= 1.0
