"""Bollinger Band z-score mean-reversion strategy (brief Section 8, "mean reversion" family).

Only proposed in SIDEWAYS or LOW_VOLATILITY regimes — mean reversion against
a strong trend is exactly the setup the regime gate exists to prevent (a
trending market can stay outside its bands far longer than a reversion
trade's stop tolerates).
"""

from __future__ import annotations

from dataclasses import dataclass

from quant_core.technical import bollinger_bands
from regime_engine.classify import Bar, RegimeResult

from strategy_engine.strategy import StrategyCandidate


@dataclass(frozen=True)
class MeanReversionStrategy:
    strategy_id: str = "mean_reversion_bollinger_v1"
    allowed_regimes: frozenset[str] = frozenset({"SIDEWAYS", "LOW_VOLATILITY"})
    window: int = 20
    num_std: float = 2.0
    horizon: str = "1h"
    estimated_costs: float = 0.002

    def generate(
        self, bars: list[Bar], regime: RegimeResult, symbol: str, venue: str
    ) -> StrategyCandidate | None:
        closes = [b["close"] for b in bars]
        upper, middle, lower = bollinger_bands(closes, self.window, self.num_std)[-1]
        entry_price = closes[-1]
        band_width = upper - lower

        if entry_price < lower:
            direction = "LONG"
            signal_strength = (
                min(1.0, (lower - entry_price) / band_width) if band_width > 0 else 0.0
            )
            stop_price = lower - band_width * 0.5
        elif entry_price > upper:
            direction = "SHORT"
            signal_strength = (
                min(1.0, (entry_price - upper) / band_width) if band_width > 0 else 0.0
            )
            stop_price = upper + band_width * 0.5
        else:
            return None

        expected_edge = abs(middle - entry_price) / entry_price

        return StrategyCandidate(
            strategyId=self.strategy_id,
            symbol=symbol,
            venue=venue,
            direction=direction,
            horizon=self.horizon,
            signalStrength=signal_strength,
            entryLogic={
                "rule": "close_beyond_bollinger_band",
                "window": self.window,
                "numStd": self.num_std,
                "upperBand": upper,
                "lowerBand": lower,
                "entryPrice": entry_price,
            },
            invalidationLogic={"rule": "close_beyond_stop_band"},
            stopLogic={"rule": "beyond_band_by_half_width", "stopPrice": stop_price},
            targetLogic={"rule": "revert_to_middle_band", "targetPrice": middle},
            expectedEdge=expected_edge,
            estimatedCosts=self.estimated_costs,
            regime=regime.label,
            timestamp=bars[-1]["timestamp"],
        )
