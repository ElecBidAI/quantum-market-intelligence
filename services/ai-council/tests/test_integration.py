"""End-to-end: bars -> regime -> candidate -> risk decision -> AI Council synthesis.

Extends services/paper-execution's integration test with an analytical
layer alongside (not instead of) the paper order — the council never
produces an order itself; brief Section 16: "Agents analyze; they do not
directly execute."
"""

from regime_engine.classify import RegimeResult, classify_regime
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

from ai_council.agents import Auditor, DevilsAdvocate, QuantAgent, RiskOfficer
from ai_council.context import CouncilContext
from ai_council.council import run_council, synthesize

THRESHOLDS = RegimeThresholds()
STRATEGIES = [TrendFollowingStrategy(), MeanReversionStrategy(), BreakoutStrategy()]
COUNCIL = [QuantAgent(), RiskOfficer(), DevilsAdvocate(), Auditor()]


def make_bars(closes, volumes=None):
    if volumes is None:
        volumes = [100.0] * len(closes)
    return [
        {"timestamp": f"t{i}", "open": c, "high": c, "low": c, "close": c, "volume": v}
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True))
    ]


def alt_noise(base, amp):
    return [c * (1 + amp * (1 if i % 2 == 0 else -1)) for i, c in enumerate(base)]


def test_council_agrees_with_an_approved_candidate():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))

    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    trend_candidate = next(c for c in candidates if c["strategyId"] == "trend_following_sma_v1")

    request = candidate_to_risk_request(trend_candidate, requested_size_pct=0.02)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0),
        RiskLimits(),
    )
    assert decision["decision"] == "APPROVE"

    context = CouncilContext(candidate=trend_candidate, regime=regime, risk_decision=decision)
    opinions = run_council(COUNCIL, context)
    thesis = synthesize(opinions)

    assert thesis.final_stance != "VETO"
    risk_officer_opinion = next(o for o in opinions if o.agent_id == "risk_officer")
    assert risk_officer_opinion.stance == "SUPPORT"


def test_council_vetoes_when_risk_engine_rejects():
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
    )
    assert decision["decision"] == "REJECT"

    context = CouncilContext(candidate=trend_candidate, regime=regime, risk_decision=decision)
    thesis = synthesize(run_council(COUNCIL, context))

    assert thesis.final_stance == "VETO"


def test_auditor_flags_a_stale_candidate_evaluated_against_a_different_regime():
    base = [100 * (1.005**i) for i in range(60)]
    bars = make_bars(alt_noise(base, 0.001))
    regime = classify_regime(bars, THRESHOLDS)
    candidates = run_strategies(STRATEGIES, bars, regime, symbol="BTC-USDT", venue="binance")
    trend_candidate = next(c for c in candidates if c["strategyId"] == "trend_following_sma_v1")

    stale_context_regime = RegimeResult(label="SIDEWAYS", confidence=0.9, metrics={})
    request = candidate_to_risk_request(trend_candidate, requested_size_pct=0.02)
    decision = evaluate(
        request,
        PortfolioState(equity=100_000.0),
        MarketContext(spread_bps=5.0, data_age_seconds=1.0),
        RiskLimits(),
    )

    context = CouncilContext(
        candidate=trend_candidate, regime=stale_context_regime, risk_decision=decision
    )
    opinions = run_council(COUNCIL, context)

    auditor_opinion = next(o for o in opinions if o.agent_id == "auditor_agent")
    assert auditor_opinion.stance == "OPPOSE"
    assert any(f.code == "REGIME_MISMATCH" for f in auditor_opinion.findings)
