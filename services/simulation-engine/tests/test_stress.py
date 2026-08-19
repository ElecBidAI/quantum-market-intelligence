import numpy as np
import pytest
from backtester.costs import TransactionCostModel

from simulation_engine.stress import (
    apply_price_shock,
    apply_volatility_multiplier,
    run_price_shock_scenario,
    stressed_cost_model,
)


def test_apply_price_shock_known_value():
    assert apply_price_shock(100, -0.20) == pytest.approx(80.0)


def test_apply_price_shock_rejects_total_wipeout():
    with pytest.raises(ValueError):
        apply_price_shock(100, -1.0)


def test_apply_price_shock_rejects_non_positive_price():
    with pytest.raises(ValueError):
        apply_price_shock(0, -0.1)


def test_apply_volatility_multiplier_known_value():
    result = apply_volatility_multiplier([1, 2, 3, 4, 5], multiplier=2.0)
    assert result.tolist() == pytest.approx([-1.0, 1.0, 3.0, 5.0, 7.0])


def test_apply_volatility_multiplier_preserves_mean():
    result = apply_volatility_multiplier([1, 2, 3, 4, 5], multiplier=3.0)
    assert np.mean(result) == pytest.approx(3.0)


def test_apply_volatility_multiplier_of_one_is_a_no_op():
    original = [1.0, 2.0, 3.0]
    result = apply_volatility_multiplier(original, multiplier=1.0)
    assert result.tolist() == pytest.approx(original)


def test_apply_volatility_multiplier_rejects_negative_multiplier():
    with pytest.raises(ValueError):
        apply_volatility_multiplier([1, 2, 3], multiplier=-1.0)


def test_stressed_cost_model_scales_only_spread():
    base = TransactionCostModel(fee_bps=10, slippage_bps=5, spread_bps=5)
    stressed = stressed_cost_model(base, spread_multiplier=5.0)
    assert stressed.fee_bps == 10
    assert stressed.slippage_bps == 5
    assert stressed.spread_bps == pytest.approx(25.0)


def test_stressed_cost_model_rejects_multiplier_below_one():
    base = TransactionCostModel()
    with pytest.raises(ValueError):
        stressed_cost_model(base, spread_multiplier=0.5)


def test_run_price_shock_scenario_known_value():
    result = run_price_shock_scenario("price_shock_-20pct", 100)
    assert result.stressed_value == pytest.approx(80.0)
    assert result.impact == pytest.approx(-20.0)
    assert result.impact_pct == pytest.approx(-0.20)


def test_run_price_shock_scenario_rejects_unknown_name():
    with pytest.raises(ValueError):
        run_price_shock_scenario("not_a_real_scenario", 100)
