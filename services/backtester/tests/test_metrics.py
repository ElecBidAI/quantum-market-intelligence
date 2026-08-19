import pytest

from backtester.metrics import (
    bonferroni_adjusted_pvalue,
    calmar_ratio,
    expectancy,
    payoff_ratio,
    profit_factor,
    recovery_factor,
    sharpe_ratio,
    sharpe_significance_pvalue,
    sortino_ratio,
    turnover,
    win_rate,
)

RETURNS = [0.01, -0.02, 0.015, 0.005, -0.01, 0.02]
EQUITY_CURVE = [
    1.0,
    1.01,
    0.9898,
    1.0046469999999998,
    1.0096702349999997,
    0.9995735326499997,
    1.0195650033029997,
]
TRADE_RETURNS = [0.05, -0.02, 0.03, -0.01, -0.04]


def test_sharpe_ratio_known_value():
    assert sharpe_ratio(RETURNS, periods_per_year=252) == pytest.approx(3.4396200248709103)


def test_sharpe_ratio_rejects_zero_variance():
    with pytest.raises(ValueError):
        sharpe_ratio([0.01, 0.01, 0.01], periods_per_year=252)


def test_sortino_ratio_known_value():
    assert sortino_ratio(RETURNS, periods_per_year=252) == pytest.approx(5.796550698475776)


def test_calmar_ratio_known_value():
    assert calmar_ratio(EQUITY_CURVE, periods_per_year=252) == pytest.approx(62.822738671860286)


def test_recovery_factor_known_value():
    assert recovery_factor(EQUITY_CURVE) == pytest.approx(0.9782501651499854)


def test_win_rate_known_value():
    assert win_rate(TRADE_RETURNS) == pytest.approx(0.4)


def test_expectancy_known_value():
    assert expectancy(TRADE_RETURNS) == pytest.approx(0.002)


def test_payoff_ratio_known_value():
    assert payoff_ratio(TRADE_RETURNS) == pytest.approx(1.7142857142857142)


def test_payoff_ratio_rejects_no_losses():
    with pytest.raises(ValueError):
        payoff_ratio([0.01, 0.02])


def test_payoff_ratio_rejects_no_wins():
    with pytest.raises(ValueError):
        payoff_ratio([-0.01, -0.02])


def test_profit_factor_known_value():
    assert profit_factor(TRADE_RETURNS) == pytest.approx(1.1428571428571428)


def test_profit_factor_rejects_no_losses():
    with pytest.raises(ValueError):
        profit_factor([0.01, 0.02])


def test_turnover_known_value():
    assert turnover([0, 1, 0, 1]) == pytest.approx(3.0)


def test_turnover_of_a_flat_book_is_zero():
    assert turnover([0, 0, 0]) == pytest.approx(0.0)


def test_sharpe_significance_pvalue_known_value():
    assert sharpe_significance_pvalue(0.15, num_periods=100) == pytest.approx(0.13361440253771617)


def test_sharpe_significance_pvalue_zero_sharpe_is_maximally_insignificant():
    assert sharpe_significance_pvalue(0.0, num_periods=100) == pytest.approx(1.0)


def test_bonferroni_adjusted_pvalue_known_value():
    p = sharpe_significance_pvalue(0.15, num_periods=100)
    assert bonferroni_adjusted_pvalue(p, num_trials=10) == pytest.approx(1.0)


def test_bonferroni_adjusted_pvalue_scales_linearly_below_the_cap():
    assert bonferroni_adjusted_pvalue(0.01, num_trials=5) == pytest.approx(0.05)


def test_bonferroni_adjusted_pvalue_caps_at_one():
    assert bonferroni_adjusted_pvalue(0.5, num_trials=10) == pytest.approx(1.0)


def test_bonferroni_adjusted_pvalue_rejects_invalid_pvalue():
    with pytest.raises(ValueError):
        bonferroni_adjusted_pvalue(1.5, num_trials=5)
