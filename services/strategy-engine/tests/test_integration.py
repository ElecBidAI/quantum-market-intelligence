"""End-to-end: bars -> regime -> strategy candidates -> risk_engine.evaluate().

This is the first point in the repository where a real StrategyCandidate
actually reaches the mandatory risk gate (docs/risk/RISK-GOVERNANCE.md) —
everything through Phase 5 built the two halves (risk_engine.evaluate() in
Phase 3; strategy candidates here in Phase 6) but nothing connected them
until strategy_engine.risk_adapter.
"""

from datetime import UTC, datetime

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

THRESHOLDS = RegimeThresholds()
STRATEGIES = [TrendFollowingStrategy(), MeanReversionStrategy(), BreakoutStrategy()]


def make_bars(closes, volumes=None):
    if volumes is None:
        volumes = [100.0] * len(closes)
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def alt_noise(base, amp):
    return [c * (1 + amp * (1 if i % 2 == 0 else -1)) for i, c in enumerate(base)]


def test_a_bullish_trend_candidate_reaches_risk_engine_and_gets_approved():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))

    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    # BULLISH_TREND is in both trend-following's and breakout's allowed_regimes, and this
    # fixture's steady climb can legitimately trigger both — assert on the one we care about.
    by_id = {c["strategyId"]: c for c in candidates}
    assert "trend_following_sma_v1" in by_id
    trend_candidate = by_id["trend_following_sma_v1"]
    assert trend_candidate["direction"] == "LONG"

    request = candidate_to_risk_request(trend_candidate, requested_size_pct=0.02)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0),
        RiskLimits(),
        now=datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC),
    )

    assert decision["decision"] == "APPROVE"
    assert decision["strategyId"] == "trend_following_sma_v1"
    assert decision["reasons"][0]["code"] == "OK"


def test_only_strategies_allowed_in_the_current_regime_reach_risk_engine():
    # SIDEWAYS: mean-reversion is allowed and may fire; trend/breakout must not.
    closes = alt_noise([100.0] * 59, 0.005)
    closes.append(closes[-1] * 0.97)
    bars = make_bars(closes)

    regime = classify_regime(bars, THRESHOLDS)
    assert regime.label == "SIDEWAYS"
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")

    assert all(c["strategyId"] == "mean_reversion_bollinger_v1" for c in candidates)


def test_kill_switch_rejects_a_candidate_that_would_otherwise_be_approved():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    request = candidate_to_risk_request(candidates[0], requested_size_pct=0.02)

    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0, kill_switch_engaged=True),
        RiskLimits(),
    )

    assert decision["decision"] == "REJECT"
    assert decision["reasons"][0]["code"] == "KILL_SWITCH_ENGAGED"


def test_oversized_candidate_is_reduced_not_silently_approved_at_full_size():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")

    # request far more size than the default 10% max-position limit allows
    request = candidate_to_risk_request(candidates[0], requested_size_pct=0.5)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0),
        RiskLimits(),
    )

    assert decision["decision"] == "REDUCE"
    assert decision["sizingAdjustment"] is not None
    assert decision["sizingAdjustment"] < 1.0
