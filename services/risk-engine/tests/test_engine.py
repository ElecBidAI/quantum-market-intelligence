import dataclasses
from datetime import UTC, datetime

import pytest

from risk_engine.engine import evaluate
from risk_engine.limits import RiskLimits
from risk_engine.state import CandidateRequest, MarketContext, PortfolioState

NOW = datetime(2026, 8, 19, 12, 0, 0, tzinfo=UTC)

# A deliberately wide-open baseline so each test can tighten exactly the one
# limit it's exercising and isolate that reason code.
LOOSE_LIMITS = RiskLimits(
    max_position_pct=1.0,
    max_asset_exposure_pct=1.0,
    max_gross_exposure_pct=1.0,
    max_net_exposure_pct=1.0,
    max_leverage=1.0,
    max_daily_loss_pct=1.0,
    max_weekly_loss_pct=1.0,
    max_portfolio_drawdown_pct=1.0,
    max_risk_per_trade_pct=1.0,
    max_portfolio_var_pct=None,
    max_spread_bps=10_000,
    max_data_age_seconds=10_000,
)


def candidate(**overrides):
    defaults = dict(
        strategy_id="trend-v1", symbol="BTC-USDT", direction="LONG", requested_size_pct=0.05
    )
    return CandidateRequest(**{**defaults, **overrides})


def portfolio(**overrides):
    defaults = dict(equity=100_000.0)
    return PortfolioState(**{**defaults, **overrides})


def market(**overrides):
    defaults = dict(spread_bps=5.0, data_age_seconds=1.0)
    return MarketContext(**{**defaults, **overrides})


def test_approves_within_all_limits():
    result = evaluate(candidate(), portfolio(), market(), LOOSE_LIMITS, now=NOW)
    assert result["decision"] == "APPROVE"
    assert result["sizingAdjustment"] is None
    assert result["reasons"][0]["code"] == "OK"
    assert result["strategyId"] == "trend-v1"
    assert result["timestamp"] == NOW.isoformat()


def test_result_shape_matches_riskDecision_contract_keys():
    result = evaluate(candidate(), portfolio(), market(), LOOSE_LIMITS, now=NOW)
    expected_keys = {"decision", "strategyId", "reasons", "sizingAdjustment", "timestamp"}
    assert set(result.keys()) == expected_keys
    assert all(set(r.keys()) == {"code", "detail"} for r in result["reasons"])


def test_rejects_when_kill_switch_engaged():
    result = evaluate(
        candidate(), portfolio(), market(kill_switch_engaged=True), LOOSE_LIMITS, now=NOW
    )
    assert result["decision"] == "REJECT"
    assert result["sizingAdjustment"] is None
    expected = [{"code": "KILL_SWITCH_ENGAGED", "detail": "global kill switch is engaged"}]
    assert result["reasons"] == expected


def test_rejects_when_circuit_breaker_engaged():
    result = evaluate(
        candidate(), portfolio(), market(circuit_breaker_engaged=True), LOOSE_LIMITS, now=NOW
    )
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "CIRCUIT_BREAKER_ENGAGED"


def test_rejects_stale_data():
    limits = dataclasses.replace(LOOSE_LIMITS, max_data_age_seconds=30)
    result = evaluate(candidate(), portfolio(), market(data_age_seconds=45), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "STALE_DATA"


def test_accepts_fresh_data_at_the_boundary():
    limits = dataclasses.replace(LOOSE_LIMITS, max_data_age_seconds=30)
    result = evaluate(candidate(), portfolio(), market(data_age_seconds=30), limits, now=NOW)
    assert result["decision"] != "REJECT"


def test_rejects_wide_spread():
    limits = dataclasses.replace(LOOSE_LIMITS, max_spread_bps=50)
    result = evaluate(candidate(), portfolio(), market(spread_bps=51), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "LIQUIDITY_SPREAD_LIMIT"


def test_rejects_max_daily_loss():
    limits = dataclasses.replace(LOOSE_LIMITS, max_daily_loss_pct=0.03)
    result = evaluate(candidate(), portfolio(daily_pnl_pct=-0.04), market(), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "MAX_DAILY_LOSS"


def test_rejects_max_weekly_loss():
    limits = dataclasses.replace(LOOSE_LIMITS, max_weekly_loss_pct=0.08)
    result = evaluate(candidate(), portfolio(weekly_pnl_pct=-0.10), market(), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "MAX_WEEKLY_LOSS"


def test_rejects_max_portfolio_drawdown():
    limits = dataclasses.replace(LOOSE_LIMITS, max_portfolio_drawdown_pct=0.20)
    result = evaluate(candidate(), portfolio(current_drawdown_pct=0.25), market(), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "MAX_PORTFOLIO_DRAWDOWN"


def test_rejects_when_portfolio_var_breached():
    limits = dataclasses.replace(LOOSE_LIMITS, max_portfolio_var_pct=0.03, var_confidence=0.90)
    bad_returns = (-0.05, -0.04, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04)
    result = evaluate(
        candidate(), portfolio(portfolio_returns=bad_returns), market(), limits, now=NOW
    )
    assert result["decision"] == "REJECT"
    assert result["reasons"][0]["code"] == "MAX_PORTFOLIO_VAR"


def test_ignores_var_gate_when_no_return_history_supplied():
    # max_portfolio_var_pct is tiny enough it would always breach if it were checked.
    limits = dataclasses.replace(LOOSE_LIMITS, max_portfolio_var_pct=0.001)
    result = evaluate(candidate(), portfolio(), market(), limits, now=NOW)
    assert result["decision"] != "REJECT"


def test_reduces_for_max_position_limit():
    limits = dataclasses.replace(LOOSE_LIMITS, max_position_pct=0.10)
    result = evaluate(
        candidate(requested_size_pct=0.15), portfolio(), market(), limits, now=NOW
    )
    assert result["decision"] == "REDUCE"
    assert result["sizingAdjustment"] == pytest.approx(0.10 / 0.15)
    assert any(r["code"] == "MAX_POSITION" for r in result["reasons"])


def test_reduces_for_max_asset_exposure_isolated_from_position_limit():
    limits = dataclasses.replace(LOOSE_LIMITS, max_asset_exposure_pct=0.10)
    result = evaluate(
        candidate(requested_size_pct=0.15), portfolio(), market(), limits, now=NOW
    )
    assert result["decision"] == "REDUCE"
    assert result["reasons"] == [
        {"code": "MAX_ASSET_EXPOSURE", "detail": "asset exposure would be 15.00%, limit is 10.00%"}
    ]


def test_reduces_for_max_gross_exposure():
    limits = dataclasses.replace(LOOSE_LIMITS, max_gross_exposure_pct=0.20)
    existing = portfolio(position_pct_by_symbol={"ETH-USDT": 0.15})
    result = evaluate(candidate(requested_size_pct=0.10), existing, market(), limits, now=NOW)
    assert result["decision"] == "REDUCE"
    # allowed_additional = 0.20 - 0.15 = 0.05; fraction = 0.05/0.10 = 0.5
    assert result["sizingAdjustment"] == pytest.approx(0.5)
    assert result["reasons"][0]["code"] == "MAX_GROSS_EXPOSURE"


def test_reduces_for_max_leverage():
    limits = dataclasses.replace(LOOSE_LIMITS, max_leverage=0.20)
    existing = portfolio(position_pct_by_symbol={"ETH-USDT": 0.15})
    result = evaluate(candidate(requested_size_pct=0.10), existing, market(), limits, now=NOW)
    assert result["decision"] == "REDUCE"
    assert result["reasons"][0]["code"] == "MAX_LEVERAGE"


def test_reduces_for_max_net_exposure():
    limits = dataclasses.replace(LOOSE_LIMITS, max_net_exposure_pct=0.10)
    result = evaluate(
        candidate(direction="LONG", requested_size_pct=0.15), portfolio(), market(), limits, now=NOW
    )
    assert result["decision"] == "REDUCE"
    assert result["reasons"][0]["code"] == "MAX_NET_EXPOSURE"


def test_short_direction_reduces_net_exposure_in_the_negative_direction():
    limits = dataclasses.replace(LOOSE_LIMITS, max_net_exposure_pct=0.10)
    short_candidate = candidate(direction="SHORT", requested_size_pct=0.15)
    result = evaluate(short_candidate, portfolio(), market(), limits, now=NOW)
    assert result["decision"] == "REDUCE"
    assert result["reasons"][0]["code"] == "MAX_NET_EXPOSURE"


def test_reduces_for_risk_per_trade_limit():
    limits = dataclasses.replace(LOOSE_LIMITS, max_risk_per_trade_pct=0.01)
    risky_candidate = candidate(requested_size_pct=0.30, stop_distance_pct=0.05)
    result = evaluate(risky_candidate, portfolio(), market(), limits, now=NOW)
    # risk-based cap = 0.01 / 0.05 = 0.20; fraction = 0.20/0.30 = 0.6667
    assert result["decision"] == "REDUCE"
    assert result["sizingAdjustment"] == pytest.approx(2 / 3)
    assert result["reasons"][0]["code"] == "RISK_PER_TRADE_LIMIT"


def test_ignores_risk_per_trade_limit_when_stop_distance_not_supplied():
    limits = dataclasses.replace(LOOSE_LIMITS, max_risk_per_trade_pct=0.001)
    result = evaluate(candidate(requested_size_pct=0.30), portfolio(), market(), limits, now=NOW)
    assert result["decision"] != "REDUCE"


def test_rejects_with_no_size_when_already_at_the_position_limit():
    limits = dataclasses.replace(LOOSE_LIMITS, max_position_pct=0.10)
    existing = portfolio(position_pct_by_symbol={"BTC-USDT": 0.10})
    result = evaluate(candidate(requested_size_pct=0.05), existing, market(), limits, now=NOW)
    assert result["decision"] == "REJECT"
    assert result["sizingAdjustment"] is None
    assert result["reasons"][0]["code"] == "MAX_POSITION"


def test_multiple_binding_caps_uses_the_tightest_and_reports_all():
    limits = dataclasses.replace(LOOSE_LIMITS, max_position_pct=0.08, max_gross_exposure_pct=0.03)
    result = evaluate(candidate(requested_size_pct=0.10), portfolio(), market(), limits, now=NOW)
    codes = {r["code"] for r in result["reasons"]}
    assert codes == {"MAX_POSITION", "MAX_GROSS_EXPOSURE"}
    # gross exposure cap (0.03/0.10 = 0.3) is tighter than position cap (0.08/0.10 = 0.8)
    assert result["sizingAdjustment"] == pytest.approx(0.3)
