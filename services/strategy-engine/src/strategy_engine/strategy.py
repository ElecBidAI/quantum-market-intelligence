"""Common strategy interface and the candidate shape (brief Section 8).

`StrategyCandidate` mirrors packages/contracts/src/strategy.ts's
`strategyCandidate` zod schema field-for-field (camelCase keys) — same
cross-language-contract-by-JSON-shape pattern as risk_engine.engine.evaluate()
mirroring `riskDecision`. A candidate is never an executable order; nothing
in this package can place one.

`Strategy` is a `Protocol`, not an ABC — Python has no first-class
"pluggable interface" mechanism beyond structural typing, and a Protocol
keeps concrete strategies free of an unnecessary base-class dependency.
"""

from __future__ import annotations

from typing import Protocol, TypedDict

from regime_engine.classify import Bar, RegimeLabel, RegimeResult

__all__ = ["Bar", "RegimeLabel", "RegimeResult", "StrategyCandidate", "Strategy"]


class StrategyCandidate(TypedDict):
    strategyId: str
    symbol: str
    venue: str
    direction: str  # "LONG" | "SHORT" | "NEUTRAL"
    horizon: str
    signalStrength: float
    entryLogic: dict[str, object]
    invalidationLogic: dict[str, object]
    stopLogic: dict[str, object]
    targetLogic: dict[str, object]
    expectedEdge: float
    estimatedCosts: float
    regime: str
    timestamp: str


class Strategy(Protocol):
    """Every concrete strategy must expose these two attributes and this method."""

    strategy_id: str
    allowed_regimes: frozenset[RegimeLabel]

    def generate(
        self, bars: list[Bar], regime: RegimeResult, symbol: str, venue: str
    ) -> StrategyCandidate | None:
        """Returns a candidate, or None if the strategy has no signal right now.

        Never called for a regime outside `allowed_regimes` — see
        `strategy_engine.engine.run_strategies`, which enforces that
        structurally rather than trusting each strategy to check it.
        """
        ...
