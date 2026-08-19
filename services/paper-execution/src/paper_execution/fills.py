"""Simulated fills (brief Section 14's "no unrealistic fills" applies here too).

Every fill is simulated to fill in full, immediately, at a price offset from
the market price by half the spread plus slippage — the same "no partial
fills / no capacity constraint" simplification `services/backtester` makes
(see its README), for the same reason: a real limit-order-book fill
simulator needs continuous order-book depth history this repository doesn't
ingest yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from paper_execution.orders import PaperOrder


@dataclass(frozen=True)
class Fill:
    order_id: str
    symbol: str
    direction: str
    size_pct: float
    price: float
    timestamp: str


@dataclass(frozen=True)
class FillSimulator:
    spread_bps: float = 5.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        if self.spread_bps < 0:
            raise ValueError("spread_bps must be non-negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative")

    def simulate_fill(self, order: PaperOrder, market_price: float, timestamp: str) -> Fill:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        sign = 1 if order.direction == "LONG" else -1
        cost_bps = self.spread_bps / 2 + self.slippage_bps
        fill_price = market_price * (1 + sign * cost_bps / 10_000)
        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            direction=order.direction,
            size_pct=order.size_pct,
            price=fill_price,
            timestamp=timestamp,
        )
