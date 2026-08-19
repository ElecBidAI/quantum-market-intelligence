import pytest

from paper_execution.fills import FillSimulator
from paper_execution.orders import PaperOrder


def make_order(direction="LONG"):
    return PaperOrder(
        order_id="o1",
        strategy_id="s1",
        symbol="BTC-USDT",
        direction=direction,
        size_pct=0.05,
        risk_decision_code="APPROVE",
        created_at="2026-08-19T00:00:00Z",
    )


def test_long_fill_pays_the_spread_and_slippage():
    simulator = FillSimulator(spread_bps=10, slippage_bps=5)
    fill = simulator.simulate_fill(make_order("LONG"), market_price=100.0, timestamp="t")
    # half spread (5bps) + slippage (5bps) = 10bps -> 100 * 1.001 = 100.1
    assert fill.price == pytest.approx(100.1)
    assert fill.direction == "LONG"
    assert fill.size_pct == pytest.approx(0.05)
    assert fill.order_id == "o1"


def test_short_fill_receives_the_spread_and_slippage_unfavorably():
    simulator = FillSimulator(spread_bps=10, slippage_bps=5)
    fill = simulator.simulate_fill(make_order("SHORT"), market_price=100.0, timestamp="t")
    assert fill.price == pytest.approx(99.9)


def test_zero_cost_simulator_fills_at_the_market_price():
    simulator = FillSimulator(spread_bps=0, slippage_bps=0)
    fill = simulator.simulate_fill(make_order("LONG"), market_price=100.0, timestamp="t")
    assert fill.price == pytest.approx(100.0)


def test_rejects_non_positive_market_price():
    simulator = FillSimulator()
    with pytest.raises(ValueError):
        simulator.simulate_fill(make_order(), market_price=0, timestamp="t")


def test_rejects_negative_cost_params():
    with pytest.raises(ValueError):
        FillSimulator(spread_bps=-1)
    with pytest.raises(ValueError):
        FillSimulator(slippage_bps=-1)
