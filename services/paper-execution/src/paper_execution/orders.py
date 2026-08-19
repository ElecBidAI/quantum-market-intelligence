"""Paper orders (brief Section 7; docs/risk/RISK-GOVERNANCE.md Section 7: "isolated execution").

`create_order_from_decision` is the isolation boundary: it is structurally
impossible to construct a `PaperOrder` from a `REJECT` decision, or from no
decision at all — the only entry point takes a risk_engine decision dict and
raises on anything but APPROVE/REDUCE. This mirrors every other structural
gate in this repo (regime, no-look-ahead, sizing caps): the rule is enforced
by what the code lets you construct, not by a convention callers are trusted
to follow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    strategy_id: str
    symbol: str
    direction: str  # "LONG" | "SHORT"
    size_pct: float  # fraction of equity, already adjusted for any REDUCE sizingAdjustment
    risk_decision_code: str  # "APPROVE" | "REDUCE" — kept for audit, never re-derived
    created_at: str


def create_order_from_decision(
    candidate: dict, risk_decision: dict, requested_size_pct: float, order_id: str | None = None
) -> PaperOrder:
    decision = risk_decision["decision"]
    if decision not in ("APPROVE", "REDUCE"):
        raise ValueError(
            f"cannot create a paper order from a {decision} decision "
            f"(reasons: {risk_decision['reasons']})"
        )
    if requested_size_pct <= 0:
        raise ValueError("requested_size_pct must be positive")

    size_pct = requested_size_pct
    if decision == "REDUCE":
        adjustment = risk_decision["sizingAdjustment"]
        if adjustment is None:
            raise ValueError("REDUCE decision is missing sizingAdjustment")
        size_pct = requested_size_pct * adjustment

    return PaperOrder(
        order_id=order_id or uuid.uuid4().hex,
        strategy_id=candidate["strategyId"],
        symbol=candidate["symbol"],
        direction=candidate["direction"],
        size_pct=size_pct,
        risk_decision_code=decision,
        created_at=candidate["timestamp"],
    )
