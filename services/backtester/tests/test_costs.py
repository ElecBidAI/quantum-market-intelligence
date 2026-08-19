import pytest

from backtester.costs import ZERO_COST, TransactionCostModel


def test_cost_known_value():
    model = TransactionCostModel(fee_bps=10, slippage_bps=5, spread_bps=5)
    # total 20bps on a full turnover of 1.0 -> 0.002
    assert model.cost(1.0) == pytest.approx(0.002)


def test_cost_scales_with_turnover():
    model = TransactionCostModel(fee_bps=10, slippage_bps=5, spread_bps=5)
    # flipping from +1 to -1 is a turnover of 2.0
    assert model.cost(2.0) == pytest.approx(0.004)


def test_zero_cost_model_charges_nothing():
    assert ZERO_COST.cost(1.0) == 0.0


def test_cost_rejects_negative_turnover():
    model = TransactionCostModel()
    with pytest.raises(ValueError):
        model.cost(-1.0)


def test_model_rejects_negative_rate():
    with pytest.raises(ValueError):
        TransactionCostModel(fee_bps=-1)
