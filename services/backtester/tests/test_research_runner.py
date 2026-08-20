from backtester.costs import ZERO_COST, TransactionCostModel
from backtester.engine import run_backtest
from backtester.research_runner import _compute_metrics, _safe

CLOSES = [100, 102, 101, 105, 103]
STANDARD_COSTS = TransactionCostModel(fee_bps=10, slippage_bps=5, spread_bps=5)


def make_bars(closes):
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": 1}
        for i, c in enumerate(closes)
    ]


def momentum_strategy(bars):
    """Same fixture strategy as backtester/tests/test_engine.py, whose
    round-trip trades for CLOSES are already independently verified there
    as two losing trades — reused here so this file doesn't need to
    hand-derive a new reference value."""
    if len(bars) < 2:
        return 0.0
    return 1.0 if bars[-1]["close"] > bars[-2]["close"] else 0.0


def test_safe_returns_the_value_when_the_function_succeeds():
    assert _safe(lambda: 1.5) == 1.5


def test_safe_returns_none_when_the_function_raises_value_error():
    def always_raises():
        raise ValueError("undefined at this sample size")

    assert _safe(always_raises) is None


def test_compute_metrics_reports_real_numbers_and_nulls_out_undefined_ones():
    bars = make_bars(CLOSES)
    result = run_backtest(bars, momentum_strategy, STANDARD_COSTS)
    metrics = _compute_metrics(bars, result)

    assert metrics["sampleSizeBars"] == len(bars)
    assert metrics["numTrades"] == 2
    assert metrics["totalReturn"] == result.total_return
    assert metrics["winRate"] == 0.0  # both round-trip trades were losses
    assert metrics["expectancy"] < 0
    assert metrics["payoffRatio"] is None  # no winning trade to form a ratio from
    assert metrics["profitFactor"] == 0.0  # no gains, but losses exist (defined, not undefined)
    assert metrics["sharpeRatio"] is not None
    assert metrics["turnover"] > 0


def test_compute_metrics_on_a_flat_strategy_nulls_out_trade_stats():
    bars = make_bars(CLOSES)
    result = run_backtest(bars, lambda _bars: 0.0, ZERO_COST)
    metrics = _compute_metrics(bars, result)

    assert metrics["numTrades"] == 0
    assert metrics["winRate"] is None
    assert metrics["expectancy"] is None
    assert metrics["payoffRatio"] is None
    assert metrics["profitFactor"] is None
    assert metrics["sharpeRatio"] is None  # zero-variance returns are undefined
