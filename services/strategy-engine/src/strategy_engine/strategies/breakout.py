"""Donchian channel breakout strategy (brief Section 8, "breakout" family).

The channel is computed from bars *before* the current one
(`bars[:-1]`) — using a channel that already includes the current bar's own
high/low would make "close breaks the channel" nearly tautological (the
current bar's high is frequently the channel's own upper bound). Comparing
the current close against the *prior* N-bar channel is what makes this a
breakout signal rather than a self-referential one.
"""

from __future__ import annotations

from dataclasses import dataclass

from quant_core.technical import donchian_channel
from regime_engine.classify import Bar, RegimeResult

from strategy_engine.strategy import StrategyCandidate


@dataclass(frozen=True)
class BreakoutStrategy:
    strategy_id: str = "breakout_donchian_v1"
    allowed_regimes: frozenset[str] = frozenset(
        {"HIGH_VOLATILITY", "BULLISH_TREND", "BEARISH_TREND"}
    )
    window: int = 20
    target_multiplier: float = 1.0
    horizon: str = "1h"
    estimated_costs: float = 0.002

    def generate(
        self, bars: list[Bar], regime: RegimeResult, symbol: str, venue: str
    ) -> StrategyCandidate | None:
        prior_bars = bars[:-1]
        highs = [b["high"] for b in prior_bars]
        lows = [b["low"] for b in prior_bars]
        upper, middle, lower = donchian_channel(highs, lows, self.window)[-1]

        entry_price = bars[-1]["close"]
        channel_width = upper - lower

        if entry_price > upper:
            direction = "LONG"
        elif entry_price < lower:
            direction = "SHORT"
        else:
            return None

        signal_strength = (
            min(1.0, abs(entry_price - middle) / channel_width) if channel_width > 0 else 0.0
        )
        sign = 1 if direction == "LONG" else -1
        target_price = entry_price + sign * channel_width * self.target_multiplier

        return StrategyCandidate(
            strategyId=self.strategy_id,
            symbol=symbol,
            venue=venue,
            direction=direction,
            horizon=self.horizon,
            signalStrength=signal_strength,
            entryLogic={
                "rule": "close_breaks_prior_donchian_channel",
                "window": self.window,
                "channelUpper": upper,
                "channelLower": lower,
                "entryPrice": entry_price,
            },
            invalidationLogic={"rule": "close_returns_inside_channel"},
            stopLogic={"rule": "retreat_to_channel_middle", "stopPrice": middle},
            targetLogic={
                "rule": "channel_width_projection",
                "targetMultiplier": self.target_multiplier,
                "targetPrice": target_price,
            },
            expectedEdge=channel_width / entry_price,
            estimatedCosts=self.estimated_costs,
            regime=regime.label,
            timestamp=bars[-1]["timestamp"],
        )
