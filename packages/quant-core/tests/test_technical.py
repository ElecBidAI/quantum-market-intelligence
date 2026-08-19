import pytest

from quant_core.technical import (
    adx,
    bollinger_bands,
    donchian_channel,
    ema,
    keltner_channel,
    macd,
    obv,
    roc,
    rsi,
    sma,
    spread_zscore,
    vwap,
)


def test_sma_known_value():
    assert sma([1, 2, 3, 4, 5], window=2) == pytest.approx([1.5, 2.5, 3.5, 4.5])


def test_sma_rejects_short_series():
    with pytest.raises(ValueError):
        sma([1, 2], window=3)


def test_ema_known_value():
    # window=3 over [1,2,3,4,5]: seed = SMA(1,2,3) = 2; alpha = 0.5
    assert ema([1, 2, 3, 4, 5], window=3) == pytest.approx([2.0, 3.0, 4.0])


def test_rsi_known_value():
    assert rsi([10, 11, 10, 12], window=2) == pytest.approx([50.0, 83.33333333333333])


def test_rsi_all_gains_is_100():
    assert rsi([1, 2, 3, 4], window=3) == pytest.approx([100.0])


def test_macd_constant_slope_gives_constant_macd():
    prices = [1, 2, 3, 4, 5, 6, 7, 8]
    macd_line, signal_line, histogram = macd(prices, fast=3, slow=5, signal=2)
    assert macd_line == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert signal_line == pytest.approx([1.0, 1.0, 1.0])
    assert histogram == pytest.approx([0.0, 0.0, 0.0], abs=1e-9)


def test_macd_rejects_fast_not_smaller_than_slow():
    with pytest.raises(ValueError):
        macd([1, 2, 3], fast=5, slow=5, signal=2)


def test_bollinger_bands_known_value():
    result = bollinger_bands([1, 2, 3, 4, 5], window=3, num_std=2)
    assert result[0] == pytest.approx((3.632993161855452, 2.0, 0.36700683814454793))
    assert result[1] == pytest.approx((4.6329931618554525, 3.0, 1.367006838144548))
    assert result[2] == pytest.approx((5.6329931618554525, 4.0, 2.367006838144548))


def test_roc_known_value():
    assert roc([10, 11, 12, 9], window=1) == pytest.approx([10.0, 9.090909090909092, -25.0])


def test_vwap_known_value():
    assert vwap([10, 11, 12], [100, 200, 100]) == pytest.approx([10.0, 10.666666666666666, 11.0])


def test_vwap_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        vwap([10, 11], [100])


def test_obv_known_value():
    assert obv([10, 11, 10, 12], [100, 150, 120, 200]) == pytest.approx([0, 150, 30, 230])


def test_donchian_channel_known_value():
    result = donchian_channel([10, 12, 11, 13], [8, 9, 7, 10], window=2)
    assert result == pytest.approx([(12, 10.0, 8), (12, 9.5, 7), (13, 10.0, 7)])


def test_keltner_channel_known_value():
    closes = [100, 102, 101, 105, 107]
    highs = [101, 103, 103, 106, 108]
    lows = [99, 100, 100, 104, 106]
    result = keltner_channel(closes, highs, lows, window=2, atr_multiplier=2)
    assert result[0] == pytest.approx((107.0, 101.0, 95.0))
    assert result[1] == pytest.approx((111.66666666666667, 103.66666666666667, 95.66666666666667))
    assert result[2] == pytest.approx((112.88888888888889, 105.88888888888889, 98.88888888888889))


def test_adx_known_value():
    highs = [30, 31, 32, 31, 33, 35, 34, 36, 37, 38]
    lows = [28, 29, 30, 29, 31, 33, 32, 34, 35, 36]
    closes = [29, 30, 31, 30, 32, 34, 33, 35, 36, 37]
    result = adx(highs, lows, closes, window=3)
    expected = [
        60.31746031746032,
        52.52395252395254,
        56.19652390485724,
        61.56589889074228,
        67.59185456159749,
    ]
    assert result == pytest.approx(expected)


def test_adx_rejects_too_few_bars():
    with pytest.raises(ValueError):
        adx([1, 2, 3], [1, 2, 3], [1, 2, 3], window=5)


def test_spread_zscore_delegates_to_rolling_normalize():
    # window=2: for a monotonically increasing spread, every z-score is exactly +1
    # (same property as transforms.rolling_normalize's own test).
    assert spread_zscore([1, 2, 3, 4], window=2) == pytest.approx([1.0, 1.0, 1.0])
