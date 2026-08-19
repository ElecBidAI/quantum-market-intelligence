"""The mandatory APPROVE/REDUCE/REJECT gate (brief Section 9; docs/risk/RISK-GOVERNANCE.md).

evaluate() is the entire public surface. It is a pure function: given a
candidate, the current portfolio state, market-quality context, and a set of
limits, it returns a decision dict shaped exactly like
packages/contracts/src/risk.ts's `riskDecision` schema (camelCase keys) so a
future TypeScript caller (or a JSON-over-the-wire boundary) doesn't need a
translation layer beyond field naming.

Decision logic, in order:

1. Hard, unconditional REJECT triggers (checked first, short-circuit):
   kill switch, circuit breaker, stale data, spread/liquidity limit, max
   daily/weekly loss, max portfolio drawdown, max portfolio VaR (only when
   portfolio_returns is supplied).
2. Sizing caps: max position, max asset exposure, max gross exposure, max
   leverage, max net exposure, and the per-trade risk budget (via
   quant_core.risk.fixed_fractional_size). Each cap that binds contributes a
   reason and an implied "approve at this fraction of the requested size."
   The tightest (smallest) fraction wins. If every cap allows zero
   additional size, the result is REJECT, not REDUCE-to-zero — a decision
   with sizingAdjustment == 0 would be indistinguishable from "not
   evaluated yet" downstream.
3. No caps bound: APPROVE at full requested size.

Every REJECT/REDUCE is explainable from `reasons` alone — no downstream
system should need to re-derive why.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quant_core.risk import fixed_fractional_size, historical_var

from risk_engine.limits import RiskLimits
from risk_engine.state import CandidateRequest, MarketContext, PortfolioState


def _reason(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _decision(
    decision: str,
    strategy_id: str,
    reasons: list[dict[str, str]],
    sizing_adjustment: float | None,
    now: datetime,
) -> dict:
    return {
        "decision": decision,
        "strategyId": strategy_id,
        "reasons": reasons,
        "sizingAdjustment": sizing_adjustment,
        "timestamp": now.isoformat(),
    }


def _hard_reject_checks(
    portfolio: PortfolioState, market: MarketContext, limits: RiskLimits
) -> tuple[str, str] | None:
    """Returns (code, detail) for the first hard-reject condition that fires, else None."""
    if market.kill_switch_engaged:
        return "KILL_SWITCH_ENGAGED", "global kill switch is engaged"
    if market.circuit_breaker_engaged:
        return "CIRCUIT_BREAKER_ENGAGED", "circuit breaker is engaged"
    if market.data_age_seconds > limits.max_data_age_seconds:
        return "STALE_DATA", (
            f"market data is {market.data_age_seconds:.1f}s old; "
            f"limit is {limits.max_data_age_seconds:.1f}s"
        )
    if market.spread_bps > limits.max_spread_bps:
        return "LIQUIDITY_SPREAD_LIMIT", (
            f"spread {market.spread_bps:.1f}bps exceeds limit {limits.max_spread_bps:.1f}bps"
        )
    if portfolio.daily_pnl_pct <= -limits.max_daily_loss_pct:
        return "MAX_DAILY_LOSS", (
            f"daily PnL {portfolio.daily_pnl_pct:.2%} "
            f"breaches limit -{limits.max_daily_loss_pct:.2%}"
        )
    if portfolio.weekly_pnl_pct <= -limits.max_weekly_loss_pct:
        return "MAX_WEEKLY_LOSS", (
            f"weekly PnL {portfolio.weekly_pnl_pct:.2%} "
            f"breaches limit -{limits.max_weekly_loss_pct:.2%}"
        )
    if portfolio.current_drawdown_pct >= limits.max_portfolio_drawdown_pct:
        return "MAX_PORTFOLIO_DRAWDOWN", (
            f"drawdown {portfolio.current_drawdown_pct:.2%} "
            f"breaches limit {limits.max_portfolio_drawdown_pct:.2%}"
        )
    if (
        limits.max_portfolio_var_pct is not None
        and portfolio.portfolio_returns is not None
        and len(portfolio.portfolio_returns) >= 2
    ):
        var = historical_var(portfolio.portfolio_returns, confidence=limits.var_confidence)
        if var > limits.max_portfolio_var_pct:
            return "MAX_PORTFOLIO_VAR", (
                f"historical VaR {var:.2%} exceeds limit {limits.max_portfolio_var_pct:.2%}"
            )
    return None


def _sizing_caps(
    candidate: CandidateRequest, portfolio: PortfolioState, limits: RiskLimits
) -> list[tuple[float, dict[str, str]]]:
    direction_sign = {"LONG": 1.0, "SHORT": -1.0, "NEUTRAL": 0.0}[candidate.direction]
    current_position = portfolio.position_pct(candidate.symbol)
    projected_position = current_position + direction_sign * candidate.requested_size_pct
    projected_gross = portfolio.gross_exposure_pct + candidate.requested_size_pct
    projected_net = portfolio.net_exposure_pct + direction_sign * candidate.requested_size_pct

    caps: list[tuple[float, dict[str, str]]] = []

    def add_cap(current: float, projected: float, limit: float, code: str, label: str) -> None:
        if abs(projected) <= limit:
            return
        allowed_additional = max(0.0, limit - abs(current))
        fraction = allowed_additional / candidate.requested_size_pct
        detail = f"{label} would be {abs(projected):.2%}, limit is {limit:.2%}"
        caps.append((fraction, _reason(code, detail)))

    add_cap(
        current_position, projected_position, limits.max_position_pct, "MAX_POSITION", "position"
    )
    add_cap(
        current_position,
        projected_position,
        limits.max_asset_exposure_pct,
        "MAX_ASSET_EXPOSURE",
        "asset exposure",
    )
    add_cap(
        portfolio.gross_exposure_pct,
        projected_gross,
        limits.max_gross_exposure_pct,
        "MAX_GROSS_EXPOSURE",
        "gross exposure",
    )
    add_cap(
        portfolio.gross_exposure_pct,
        projected_gross,
        limits.max_leverage,
        "MAX_LEVERAGE",
        "leverage",
    )
    add_cap(
        portfolio.net_exposure_pct,
        projected_net,
        limits.max_net_exposure_pct,
        "MAX_NET_EXPOSURE",
        "net exposure",
    )

    if candidate.stop_distance_pct is not None:
        risk_based_cap_pct = fixed_fractional_size(
            equity=1.0,
            risk_fraction=limits.max_risk_per_trade_pct,
            stop_distance=candidate.stop_distance_pct,
        )
        if candidate.requested_size_pct > risk_based_cap_pct:
            fraction = risk_based_cap_pct / candidate.requested_size_pct
            detail = (
                f"requested size {candidate.requested_size_pct:.2%} risks more than "
                f"{limits.max_risk_per_trade_pct:.2%} of equity "
                f"at a {candidate.stop_distance_pct:.2%} stop"
            )
            caps.append((fraction, _reason("RISK_PER_TRADE_LIMIT", detail)))

    return caps


def evaluate(
    candidate: CandidateRequest,
    portfolio: PortfolioState,
    market: MarketContext,
    limits: RiskLimits,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)

    hard_reject = _hard_reject_checks(portfolio, market, limits)
    if hard_reject is not None:
        code, detail = hard_reject
        return _decision("REJECT", candidate.strategy_id, [_reason(code, detail)], None, now)

    caps = _sizing_caps(candidate, portfolio, limits)
    if not caps:
        ok = [_reason("OK", "within all configured risk limits")]
        return _decision("APPROVE", candidate.strategy_id, ok, None, now)

    binding_fraction = min(fraction for fraction, _ in caps)
    reasons = [reason for _, reason in caps]

    if binding_fraction <= 0:
        return _decision("REJECT", candidate.strategy_id, reasons, None, now)
    return _decision("REDUCE", candidate.strategy_id, reasons, binding_fraction, now)
