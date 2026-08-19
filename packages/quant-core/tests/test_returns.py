import math

import pytest

from quant_core.returns import (
    annualized_return,
    cumulative_return,
    log_return,
    log_returns,
    simple_return,
    simple_returns,
)


def test_simple_return_known_value():
    # 100 -> 110 is a 10% simple return.
    assert simple_return(100, 110) == pytest.approx(0.10)


def test_simple_return_negative_move():
    assert simple_return(100, 90) == pytest.approx(-0.10)


def test_simple_return_rejects_zero_start():
    with pytest.raises(ValueError):
        simple_return(0, 100)


def test_log_return_known_value():
    # ln(110/100) ~= 0.09531017980432486
    assert log_return(100, 110) == pytest.approx(math.log(1.1))


def test_log_return_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        log_return(0, 100)
    with pytest.raises(ValueError):
        log_return(100, -5)


def test_simple_returns_series():
    prices = [100, 110, 121]
    result = simple_returns(prices)
    assert result == pytest.approx([0.10, 0.10])


def test_simple_returns_requires_two_prices():
    with pytest.raises(ValueError):
        simple_returns([100])


def test_log_returns_series():
    prices = [100, 110, 121]
    result = log_returns(prices)
    assert result == pytest.approx([math.log(1.1), math.log(1.1)])


def test_cumulative_return_compounds_not_sums():
    # Two consecutive +10% periods compound to 21%, not 20%.
    assert cumulative_return([0.10, 0.10]) == pytest.approx(0.21)


def test_cumulative_return_handles_a_loss_then_gain():
    # -50% then +100% nets to 0%, the classic compounding trap.
    assert cumulative_return([-0.5, 1.0]) == pytest.approx(0.0)


def test_cumulative_return_rejects_empty_sequence():
    with pytest.raises(ValueError):
        cumulative_return([])


def test_annualized_return_known_value():
    # 10% over 6 months (of a 12-month year) annualizes to 1.1^2 - 1 = 21%.
    assert annualized_return(0.10, periods=6, periods_per_year=12) == pytest.approx(0.21)


def test_annualized_return_rejects_non_positive_periods():
    with pytest.raises(ValueError):
        annualized_return(0.10, periods=0, periods_per_year=12)


def test_annualized_return_rejects_total_wipeout_below_negative_100_percent():
    with pytest.raises(ValueError):
        annualized_return(-1.5, periods=6, periods_per_year=12)
