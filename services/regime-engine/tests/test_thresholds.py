import pytest

from regime_engine.thresholds import RegimeThresholds


def test_defaults_are_valid():
    RegimeThresholds()  # must not raise


def test_rejects_fast_window_not_smaller_than_slow():
    with pytest.raises(ValueError):
        RegimeThresholds(sma_fast_window=50, sma_slow_window=50)


def test_rejects_high_vol_threshold_not_greater_than_low():
    with pytest.raises(ValueError):
        RegimeThresholds(high_volatility_threshold=0.005, low_volatility_threshold=0.01)


def test_rejects_non_positive_trend_threshold():
    with pytest.raises(ValueError):
        RegimeThresholds(trend_threshold=0)


def test_rejects_out_of_range_accumulation_ratio():
    with pytest.raises(ValueError):
        RegimeThresholds(accumulation_obv_ratio=1.5)
