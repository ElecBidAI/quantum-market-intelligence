"""End-to-end: bars -> regime -> candidate -> risk decision -> paper order -> fill -> position.

Extends services/strategy-engine/tests/test_integration.py (which stops at
risk_engine.evaluate()) all the way through simulated execution — the full
chain from brief Section 25: "Data -> Quality -> Mathematics -> Statistical
Evidence -> Regime -> Strategy Candidate -> Risk -> Portfolio -> Simulation
-> Paper Execution -> Measurement -> Learning," minus the Quality/Portfolio/
Simulation steps this particular walk doesn't exercise (those are proven
independently in their own services' tests).
"""

from datetime import UTC, datetime

import pytest
from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds
from risk_engine.engine import evaluate
from risk_engine.limits import RiskLimits
from risk_engine.state import MarketContext, PortfolioState
from strategy_engine.engine import run_strategies
from strategy_engine.risk_adapter import candidate_to_risk_request
from strategy_engine.strategies import (
    BreakoutStrategy,
    MeanReversionStrategy,
    TrendFollowingStrategy,
)

from paper_execution.analytics import summarize_trades
from paper_execution.fills import Fill, FillSimulator
from paper_execution.orders import create_order_from_decision
from paper_execution.positions import PositionBook, reconcile

THRESHOLDS = RegimeThresholds()
STRATEGIES = [TrendFollowingStrategy(), MeanReversionStrategy(), BreakoutStrategy()]
NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)


def make_bars(closes, volumes=None):
    if volumes is None:
        volumes = [100.0] * len(closes)
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def alt_noise(base, amp):
    return [c * (1 + amp * (1 if i % 2 == 0 else -1)) for i, c in enumerate(base)]


def test_full_pipeline_from_bars_to_a_filled_paper_position():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    market_price = bars[-1]["close"]

    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    trend_candidate = next(c for c in candidates if c["strategyId"] == "trend_following_sma_v1")

    request = candidate_to_risk_request(trend_candidate, requested_size_pct=0.02)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0),
        RiskLimits(),
        now=NOW,
    )
    assert decision["decision"] == "APPROVE"

    order = create_order_from_decision(
        trend_candidate, decision, requested_size_pct=0.02, order_id="order-1"
    )
    assert order.risk_decision_code == "APPROVE"

    fill = FillSimulator(spread_bps=5, slippage_bps=5).simulate_fill(
        order, market_price=market_price, timestamp=trend_candidate["timestamp"]
    )
    assert fill.direction == "LONG"
    assert fill.size_pct == order.size_pct

    book = PositionBook()
    book.apply_fill(fill)

    position = book.positions["BTC-USDT"]
    assert position.net_size == order.size_pct
    assert position.avg_entry_price == fill.price
    assert reconcile(book, [fill]) == []


def test_a_reject_decision_never_reaches_a_fill():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    trend_candidate = next(c for c in candidates if c["strategyId"] == "trend_following_sma_v1")

    request = candidate_to_risk_request(trend_candidate, requested_size_pct=0.02)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0, kill_switch_engaged=True),
        RiskLimits(),
        now=NOW,
    )
    assert decision["decision"] == "REJECT"

    with pytest.raises(ValueError):
        create_order_from_decision(trend_candidate, decision, requested_size_pct=0.02)


def test_round_trip_close_feeds_analytics():
    book = PositionBook()
    book.apply_fill(_fill("LONG", 0.05, 100.0))
    book.apply_fill(_fill("SHORT", 0.05, 108.0))  # closes for an 8% gain

    summary = summarize_trades(book.closed_trade_returns)
    assert summary["trade_count"] == 1
    assert summary["win_rate"] == 1.0


def _fill(direction, size_pct, price):
    return Fill(
        order_id="o",
        symbol="BTC-USDT",
        direction=direction,
        size_pct=size_pct,
        price=price,
        timestamp="t",
    )
