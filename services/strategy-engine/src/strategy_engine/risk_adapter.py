"""Converts a StrategyCandidate into risk_engine's CandidateRequest.

This is the concrete answer to "how does a candidate reach the mandatory
risk gate" (docs/risk/RISK-GOVERNANCE.md) — the only wiring that was still
missing after Phase 3 built risk_engine.evaluate() with nothing yet calling
it. strategy-engine does not depend on risk-engine at the package level
(same no-path-dependency situation as every other cross-package Python
import in this repo — see services/feature-engine/README.md); both must be
installed editable into the same environment.

`requested_size_pct` is deliberately a caller-supplied argument, not derived
from the candidate — sizing is risk-engine's job (its per-trade risk budget,
`RiskLimits.max_risk_per_trade_pct`), not strategy-engine's. A strategy
proposes a direction and a stop; how much capital to actually risk on it is
a risk decision, not a strategy decision.
"""

from __future__ import annotations

from risk_engine.state import CandidateRequest

from strategy_engine.strategy import StrategyCandidate


def candidate_to_risk_request(
    candidate: StrategyCandidate, requested_size_pct: float
) -> CandidateRequest:
    stop_distance_pct = _extract_stop_distance_pct(candidate)
    return CandidateRequest(
        strategy_id=candidate["strategyId"],
        symbol=candidate["symbol"],
        direction=candidate["direction"],
        requested_size_pct=requested_size_pct,
        stop_distance_pct=stop_distance_pct,
    )


def _extract_stop_distance_pct(candidate: StrategyCandidate) -> float | None:
    """Derives stop distance from entryLogic["entryPrice"]/stopLogic["stopPrice"] when present.

    Both are free-form dicts by contract (packages/contracts/src/strategy.ts:
    entryLogic/stopLogic are `Record<string, unknown>`) — every strategy in
    this repo happens to populate these two keys, but a hypothetical future
    strategy that doesn't gets None here, and simply skips risk-engine's
    per-trade risk-budget check rather than crashing or fabricating a stop
    distance that was never actually specified.
    """
    entry_price = candidate["entryLogic"].get("entryPrice")
    stop_price = candidate["stopLogic"].get("stopPrice")
    if not isinstance(entry_price, int | float) or not isinstance(stop_price, int | float):
        return None
    if entry_price == 0:
        return None
    return abs(entry_price - stop_price) / entry_price
