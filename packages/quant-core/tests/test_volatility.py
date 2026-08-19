import math

import pytest

from quant_core.volatility import (
    atr,
    ewma_volatility,
    garman_klass_volatility,
    parkinson_volatility,
    realized_volatility,
    rogers_satchell_volatility,
    rolling_volatility,
)


def test_rolling_volatility_known_value():
    # window=2 over [1,2,3,4,5]: each pair has sample std_dev = |b-a|/sqrt(2)
    result = rolling_volatility([1, 2, 3, 4, 5], window=2)
    assert result == pytest.approx([1 / math.sqrt(2)] * 4)


def test_rolling_volatility_rejects_short_series():
    with pytest.raises(ValueError):
        rolling_volatility([1, 2], window=3)


def test_realized_volatility_known_value():
    returns = [0.01, -0.02, 0.015, -0.005]
    assert realized_volatility(returns, periods_per_year=252) == pytest.approx(0.21737065119284157)


def test_realized_volatility_rejects_empty():
    with pytest.raises(ValueError):
        realized_volatility([], periods_per_year=252)


def test_ewma_volatility_known_value():
    # hand-traceable with lambda=0.5: var0=0.02^2, var1=0.5*var0+0.5*(-0.01)^2,
    # var2=0.5*var1+0.5*0.03^2 -> vol = sqrt(var2)
    assert ewma_volatility([0.02, -0.01, 0.03], lambda_=0.5) == pytest.approx(0.023979157616563596)


def test_ewma_volatility_rejects_invalid_lambda():
    with pytest.raises(ValueError):
        ewma_volatility([0.01], lambda_=1.5)


def test_parkinson_volatility_known_value():
    # single bar with H/L = e, so ln(H/L)^2 = 1; ppy=1 isolates the formula's constant.
    result = parkinson_volatility([math.e * 10], [10], periods_per_year=1)
    assert result == pytest.approx(0.6005612043932249)


def test_garman_klass_volatility_known_value():
    result = garman_klass_volatility([10], [12], [9], [11], periods_per_year=1)
    assert result == pytest.approx(0.19460569800298574)


def test_rogers_satchell_volatility_known_value():
    result = rogers_satchell_volatility([10], [12], [9], [11], periods_per_year=1)
    assert result == pytest.approx(0.1923715614711328)


def test_ohlc_estimators_reject_mismatched_lengths():
    with pytest.raises(ValueError):
        garman_klass_volatility([10, 11], [12], [9], [11], periods_per_year=1)


def test_atr_known_value():
    # hand-traced Wilder ATR, window=2 (see commit context for the trace).
    highs = [101, 103, 103, 106]
    lows = [99, 100, 100, 104]
    closes = [100, 102, 101, 105]
    assert atr(highs, lows, closes, window=2) == pytest.approx([3.0, 4.0])


def test_atr_rejects_too_few_bars():
    with pytest.raises(ValueError):
        atr([101, 103], [99, 100], [100, 102], window=5)
