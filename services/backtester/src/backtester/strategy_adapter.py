"""Adapts a strategy_engine.Strategy into the backtester's StrategyFn shape.

This is exactly the wiring `strategy_engine`'s own strategies name as
missing (see e.g. trend_following.py's docstring, before this module
existed: "a real edge estimate would come from running this exact strategy
through services/backtester over historical data... but nothing wires a
strategy's live candidate generation to its own backtested track record
yet"). `engine.run_backtest` wants `strategy_fn(bars[:t+1]) -> position in
[-1, 1]`; a `Strategy.generate()` returns a `StrategyCandidate | None`
instead — this closure bridges the two without changing either interface.

Every "not enough information yet" case (too few bars for regime
classification, regime not in the strategy's allowed set, a technical
indicator whose window is still larger than the available bars, no
candidate) returns a flat `0.0` position rather than raising — a backtest
walking forward bar-by-bar from an empty history hits this constantly by
construction, and it must be treated as "no signal," not an error.
"""

from __future__ import annotations

from collections.abc import Sequence

from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds
from strategy_engine.strategy import Strategy

from backtester.engine import Bar, StrategyFn

_DIRECTION_SIGN = {"LONG": 1.0, "SHORT": -1.0, "NEUTRAL": 0.0}


def strategy_to_position_fn(
    strategy: Strategy,
    symbol: str,
    venue: str,
    thresholds: RegimeThresholds | None = None,
) -> StrategyFn:
    thresholds = thresholds or RegimeThresholds()
    min_bars = max(
        thresholds.sma_slow_window, thresholds.volatility_window + 1, thresholds.obv_window
    )

    def position_fn(bars: Sequence[Bar]) -> float:
        if len(bars) < min_bars:
            return 0.0

        regime = classify_regime(list(bars), thresholds)
        if regime.label not in strategy.allowed_regimes:
            return 0.0

        try:
            candidate = strategy.generate(list(bars), regime, symbol, venue)
        except ValueError:
            # A technical indicator's own window (e.g. trend_following's
            # 50-bar slow SMA) is still larger than what's available at
            # this point in the walk — honestly "no signal yet."
            return 0.0

        if candidate is None:
            return 0.0

        sign = _DIRECTION_SIGN.get(candidate["direction"], 0.0)
        return sign * candidate["signalStrength"]

    return position_fn
