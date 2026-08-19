import pytest

from feature_engine.features import Bar, compute_features, periods_per_year_for_interval


def make_bars(closes: list[float]) -> list[Bar]:
    """Flat-OHLC synthetic bars (open=high=low=close) — fine for every
    feature computed here except it would be a degenerate input for
    something like Parkinson vol (not used in this feature set)."""
    return [
        Bar(
            timestamp=f"2026-08-19T00:{i:02d}:00.000Z",
            open=c,
            high=c,
            low=c,
            close=c,
            volume=100 + i,
        )
        for i, c in enumerate(closes)
    ]


def test_periods_per_year_for_interval_known_values():
    assert periods_per_year_for_interval("1m") == 365 * 24 * 60
    assert periods_per_year_for_interval("1d") == 365


def test_periods_per_year_for_interval_rejects_unknown():
    with pytest.raises(ValueError):
        periods_per_year_for_interval("3w")


def test_compute_features_rejects_empty_bars():
    with pytest.raises(ValueError):
        compute_features([], "1m")


def test_compute_features_with_minimal_history():
    # Only 3 bars: not enough for almost anything, but last_close and the
    # lowest-order return stats should still come through.
    bars = make_bars([100, 101, 99])
    features = compute_features(bars, "1m")

    assert features["last_close"] == 99
    assert features["mean_log_return"] is not None
    assert features["std_log_return"] is not None
    # skewness needs >= 3 log returns; there are only 2 here
    assert features["skewness_log_return"] is None
    assert features["sma_20"] is None
    assert features["rsi_14"] is None
    assert features["macd_line"] is None
    assert features["bollinger_upper_20"] is None


def test_compute_features_with_enough_history_for_medium_windows():
    closes = [100 + i * 0.1 for i in range(30)]
    bars = make_bars(closes)
    features = compute_features(bars, "1m")

    assert features["sma_20"] is not None
    assert features["ema_20"] is not None
    assert features["rsi_14"] is not None
    assert features["roc_10"] is not None
    assert features["atr_14"] is not None
    assert features["skewness_log_return"] is not None
    assert features["kurtosis_log_return"] is not None
    # MACD needs slow(26) + signal(9) - 1 = 34 bars; 30 isn't enough yet
    assert features["macd_line"] is None


def test_compute_features_with_enough_history_for_macd():
    closes = [100 + i * 0.1 for i in range(40)]
    bars = make_bars(closes)
    features = compute_features(bars, "1m")

    assert features["macd_line"] is not None
    assert features["macd_signal"] is not None
    assert features["macd_histogram"] is not None
    upper, middle, lower = (
        features["bollinger_upper_20"],
        features["bollinger_middle_20"],
        features["bollinger_lower_20"],
    )
    assert upper is not None
    assert upper >= middle >= lower


def test_compute_features_carries_feature_set_and_timestamp():
    bars = make_bars([100, 101, 102])
    features = compute_features(bars, "1m")
    assert features["feature_set"] == "phase2-v1"
    assert features["timestamp"] == bars[-1]["timestamp"]
