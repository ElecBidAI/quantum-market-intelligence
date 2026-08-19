import pytest

from quant_core.risk import (
    atr_based_size,
    beta,
    concentration_hhi,
    cvar,
    downside_deviation,
    fixed_fractional_size,
    fractional_kelly_size,
    gross_exposure,
    historical_var,
    information_ratio,
    max_drawdown,
    net_exposure,
    omega_ratio,
    parametric_var,
    tracking_error,
    ulcer_index,
    volatility_target_size,
)

RETURNS = [-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05]


def test_historical_var_known_value():
    assert historical_var(RETURNS, confidence=0.90) == pytest.approx(0.05)


def test_historical_var_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        historical_var(RETURNS, confidence=1.5)


def test_parametric_var_known_value():
    assert parametric_var(RETURNS, confidence=0.95) == pytest.approx(0.048703807068730384)


def test_cvar_known_value():
    assert cvar(RETURNS, confidence=0.90) == pytest.approx(0.05)


def test_cvar_at_least_as_large_as_var():
    # CVaR (tail average) is never smaller than VaR (tail cutoff) by construction.
    assert cvar(RETURNS, confidence=0.80) >= historical_var(RETURNS, confidence=0.80)


def test_max_drawdown_known_value():
    equity = [100, 110, 105, 120, 90, 95, 130]
    assert max_drawdown(equity) == pytest.approx(0.25)


def test_max_drawdown_is_zero_for_monotonic_growth():
    assert max_drawdown([100, 110, 120, 130]) == pytest.approx(0.0)


def test_max_drawdown_rejects_non_positive_start():
    with pytest.raises(ValueError):
        max_drawdown([0, 10, 20])


def test_downside_deviation_known_value():
    assert downside_deviation(RETURNS) == pytest.approx(0.0197484176581315)


def test_downside_deviation_is_zero_when_no_returns_below_target():
    assert downside_deviation([0.01, 0.02, 0.03]) == pytest.approx(0.0)


def test_ulcer_index_known_value():
    equity = [100, 110, 105, 120, 90, 95, 130]
    assert ulcer_index(equity) == pytest.approx(12.419391144511366)


def test_beta_known_value():
    asset = [0.01, 0.02, -0.01, 0.03, -0.02]
    bench = [0.005, 0.015, -0.005, 0.02, -0.01]
    assert beta(asset, bench) == pytest.approx(1.6153846153846154)


def test_beta_of_benchmark_against_itself_is_one():
    bench = [0.01, -0.02, 0.03, -0.01]
    assert beta(bench, bench) == pytest.approx(1.0)


def test_tracking_error_and_information_ratio_known_values():
    asset = [0.01, 0.02, -0.01, 0.03, -0.02]
    bench = [0.005, 0.015, -0.005, 0.02, -0.01]
    assert tracking_error(asset, bench) == pytest.approx(0.008215838362577492)
    assert information_ratio(asset, bench) == pytest.approx(0.12171612389003689)


def test_omega_ratio_known_value():
    assert omega_ratio(RETURNS) == pytest.approx(1.3636363636363635)


def test_omega_ratio_rejects_no_losses():
    with pytest.raises(ValueError):
        omega_ratio([0.01, 0.02, 0.03])


def test_fixed_fractional_size_known_value():
    result = fixed_fractional_size(equity=10_000, risk_fraction=0.01, stop_distance=50)
    assert result == pytest.approx(2.0)


def test_fixed_fractional_size_rejects_invalid_risk_fraction():
    with pytest.raises(ValueError):
        fixed_fractional_size(equity=10_000, risk_fraction=1.5, stop_distance=50)


def test_atr_based_size_known_value():
    result = atr_based_size(equity=10_000, risk_fraction=0.01, atr=25, atr_multiplier=2.0)
    assert result == pytest.approx(2.0)


def test_volatility_target_size_known_value():
    result = volatility_target_size(equity=10_000, target_volatility=0.02, asset_volatility=0.04)
    assert result == pytest.approx(5_000)


def test_fractional_kelly_size_known_value():
    result = fractional_kelly_size(win_probability=0.6, win_loss_ratio=2.0, fraction=0.5)
    assert result == pytest.approx(0.2)


def test_fractional_kelly_size_clamps_negative_edge_to_zero():
    # p=0.3, b=1 -> full kelly = 0.3 - 0.7/1 = -0.4 -> clamped to 0
    result = fractional_kelly_size(win_probability=0.3, win_loss_ratio=1.0, fraction=0.5)
    assert result == pytest.approx(0.0)


def test_gross_and_net_exposure_known_values():
    weights = [0.3, -0.2, 0.1]
    assert gross_exposure(weights) == pytest.approx(0.6)
    assert net_exposure(weights) == pytest.approx(0.2)


def test_concentration_hhi_equal_weights():
    assert concentration_hhi([0.5, 0.5]) == pytest.approx(0.5)


def test_concentration_hhi_single_position_is_one():
    assert concentration_hhi([1.0]) == pytest.approx(1.0)


def test_concentration_hhi_zero_gross_exposure_is_zero():
    assert concentration_hhi([0.0, 0.0]) == pytest.approx(0.0)
