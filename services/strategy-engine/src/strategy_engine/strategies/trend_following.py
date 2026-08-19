"""SMA-crossover trend-following strategy (brief Section 8, "trend following" family).

Only ever proposed in a trend regime that agrees with the crossover
direction (BULLISH_TREND + fast SMA above slow, or BEARISH_TREND + fast SMA
below slow) — a trending regime with a crossover pointing the *other* way
produces no candidate, since that's a conflicting signal, not a confirming
one.

`expected_edge` is a naive placeholder (the SMA spread itself, as a
fraction) — not a backtested estimate. A real edge estimate would come from
running this exact strategy through `services/backtester` over historical
data; this repository has that capability (Phase 4) but nothing wires a
strategy's live candidate generation to its own backtested track record yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from quant_core.technical import sma
from quant_core.volatility import atr
from regime_engine.classify import Bar, RegimeResult

from strategy_engine.strategy import StrategyCandidate


@dataclass(frozen=True)
class TrendFollowingStrategy:
    strategy_id: str = "trend_following_sma_v1"
    allowed_regimes: frozenset[str] = frozenset({"BULLISH_TREND", "BEARISH_TREND"})
    fast_window: int = 20
    slow_window: int = 50
    atr_window: int = 14
    atr_multiplier: float = 2.0
    reward_risk_ratio: float = 2.0
    horizon: str = "4h"
    estimated_costs: float = 0.002

    def generate(
        self, bars: list[Bar], regime: RegimeResult, symbol: str, venue: str
    ) -> StrategyCandidate | None:
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]

        sma_fast = sma(closes, self.fast_window)[-1]
        sma_slow = sma(closes, self.slow_window)[-1]

        if regime.label == "BULLISH_TREND" and sma_fast > sma_slow:
            direction = "LONG"
        elif regime.label == "BEARISH_TREND" and sma_fast < sma_slow:
            direction = "SHORT"
        else:
            return None

        atr_value = atr(highs, lows, closes, self.atr_window)[-1]
        entry_price = closes[-1]
        stop_distance = atr_value * self.atr_multiplier
        sign = 1 if direction == "LONG" else -1
        stop_price = entry_price - sign * stop_distance
        target_price = entry_price + sign * stop_distance * self.reward_risk_ratio

        return StrategyCandidate(
            strategyId=self.strategy_id,
            symbol=symbol,
            venue=venue,
            direction=direction,
            horizon=self.horizon,
            signalStrength=regime.confidence,
            entryLogic={
                "rule": "sma_fast_crosses_sma_slow_in_trend_direction",
                "fastWindow": self.fast_window,
                "slowWindow": self.slow_window,
                "smaFast": sma_fast,
                "smaSlow": sma_slow,
                "entryPrice": entry_price,
            },
            invalidationLogic={"rule": "sma_fast_crosses_back_over_sma_slow"},
            stopLogic={
                "rule": "atr_multiple",
                "atrWindow": self.atr_window,
                "atrMultiplier": self.atr_multiplier,
                "stopPrice": stop_price,
            },
            targetLogic={
                "rule": "reward_risk_multiple",
                "rewardRiskRatio": self.reward_risk_ratio,
                "targetPrice": target_price,
            },
            expectedEdge=abs(sma_fast - sma_slow) / sma_slow,
            estimatedCosts=self.estimated_costs,
            regime=regime.label,
            timestamp=bars[-1]["timestamp"],
        )
