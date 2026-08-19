import pytest

from backtester.costs import ZERO_COST, TransactionCostModel
from backtester.engine import extract_round_trip_trades, run_backtest

CLOSES = [100, 102, 101, 105, 103]
STANDARD_COSTS = TransactionCostModel(fee_bps=10, slippage_bps=5, spread_bps=5)


def make_bars(closes):
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": 1}
        for i, c in enumerate(closes)
    ]


def momentum_strategy(bars):
    """Go long (1) iff the last close is higher than the one before it; else flat."""
    if len(bars) < 2:
        return 0.0
    return 1.0 if bars[-1]["close"] > bars[-2]["close"] else 0.0


def test_run_backtest_matches_hand_traced_reference():
    bars = make_bars(CLOSES)
    result = run_backtest(bars, momentum_strategy, STANDARD_COSTS, initial_equity=1.0)

    assert result.positions_held == [0, 1, 0, 1]
    expected_equity = [1.0, 1.0, 0.9882156862745098, 0.9862392549019608, 0.965518837794211]
    assert result.equity_curve == pytest.approx(expected_equity)


def test_run_backtest_never_sees_future_bars():
    """Changing a future bar's price must not change a decision made before it existed."""
    bars = make_bars(CLOSES)
    seen_lengths = []

    def recording_strategy(visible_bars):
        seen_lengths.append(len(visible_bars))
        return momentum_strategy(visible_bars)

    run_backtest(bars, recording_strategy, ZERO_COST)
    # called once per step (len(bars)-1 times), each time with an ever-growing
    # prefix that never includes bars beyond the current step
    assert seen_lengths == [1, 2, 3, 4]


def test_run_backtest_is_deterministic():
    bars = make_bars(CLOSES)
    model = TransactionCostModel()
    result_a = run_backtest(bars, momentum_strategy, model)
    result_b = run_backtest(bars, momentum_strategy, model)
    assert result_a.equity_curve == result_b.equity_curve
    assert result_a.positions_held == result_b.positions_held


def test_run_backtest_zero_cost_flat_strategy_leaves_equity_unchanged():
    bars = make_bars(CLOSES)
    result = run_backtest(bars, lambda _bars: 0.0, ZERO_COST, initial_equity=100.0)
    assert result.equity_curve == pytest.approx([100.0] * len(bars))


def test_run_backtest_charges_a_cost_on_every_position_change():
    bars = make_bars(CLOSES)
    costs = TransactionCostModel(fee_bps=20, slippage_bps=0, spread_bps=0)
    result = run_backtest(bars, momentum_strategy, costs)
    # positions [0,1,0,1] against an initial position of 0: turnover events at
    # every step here (0->1, 1->0, 0->1)
    assert len(result.turnover_events) == 3
    assert all(e.cost > 0 for e in result.turnover_events)


def test_run_backtest_rejects_out_of_range_signal():
    bars = make_bars(CLOSES)
    with pytest.raises(ValueError):
        run_backtest(bars, lambda _bars: 2.0, ZERO_COST)


def test_run_backtest_rejects_too_few_bars():
    with pytest.raises(ValueError):
        run_backtest(make_bars([100]), momentum_strategy, ZERO_COST)


def test_total_return_property():
    bars = make_bars(CLOSES)
    result = run_backtest(bars, momentum_strategy, STANDARD_COSTS)
    expected = result.equity_curve[-1] / result.equity_curve[0] - 1
    assert result.total_return == pytest.approx(expected)


class TestExtractRoundTripTrades:
    def test_known_value(self):
        bars = make_bars(CLOSES)
        result = run_backtest(bars, momentum_strategy, STANDARD_COSTS)
        trades = extract_round_trip_trades(result.positions_held, result.equity_curve)
        assert trades == pytest.approx([-0.011784313725490159, -0.021009523809523922])

    def test_a_direct_flip_is_two_trades(self):
        # positions +1, -1: the flip must close the long and open the short,
        # not be treated as one continuous trade.
        equity_curve = [1.0, 1.1, 0.99]
        trades = extract_round_trip_trades([1, -1], equity_curve)
        assert len(trades) == 2
        assert trades[0] == pytest.approx(0.1)
        assert trades[1] == pytest.approx(0.99 / 1.1 - 1)

    def test_all_flat_yields_no_trades(self):
        equity_curve = [1.0, 1.0, 1.0]
        assert extract_round_trip_trades([0, 0], equity_curve) == []

    def test_rejects_mismatched_lengths(self):
        with pytest.raises(ValueError):
            extract_round_trip_trades([0, 1], [1.0, 1.0])
