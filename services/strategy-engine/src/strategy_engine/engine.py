"""Runs a set of strategies against the current bars/regime (brief Section 8).

The regime gate (brief Section 7: "Strategies must declare the regimes in
which they are allowed to operate") is enforced here, structurally: a
strategy's `generate()` is never even called when the current regime isn't
in its `allowed_regimes`. This is deliberate — a strategy that ignored its
own declared regimes would be trusted to self-police, the same trust
`risk_engine` and `backtester` are built to not require.
"""

from __future__ import annotations

from regime_engine.classify import Bar, RegimeResult

from strategy_engine.strategy import Strategy, StrategyCandidate


def run_strategies(
    strategies: list[Strategy], bars: list[Bar], regime: RegimeResult, symbol: str, venue: str
) -> list[StrategyCandidate]:
    candidates = []
    for strategy in strategies:
        if regime.label not in strategy.allowed_regimes:
            continue
        candidate = strategy.generate(bars, regime, symbol, venue)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
