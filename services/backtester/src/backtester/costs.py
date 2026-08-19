"""Transaction cost model (brief Section 14, "Include fees/spread/slippage/latency").

Costs are modeled as a single proportional charge against turnover — the
fraction of position changed, times a combined bps rate. This is a
deliberate simplification: it is not a limit-order-book fill simulator (no
partial fills, no depth-dependent slippage). See engine.py's module
docstring for what that would take and why it's deferred.

Latency is not separately modeled: signals are already executed one bar
later than they're decided (engine.py), which is the discrete-time
equivalent of "you can't act on data before it exists." A finer-grained
latency model needs sub-bar timestamps, which 1m OHLCV bars don't have.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostModel:
    """Combined proportional cost rate, expressed in basis points of turnover."""

    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    spread_bps: float = 5.0

    def __post_init__(self) -> None:
        for name in ("fee_bps", "slippage_bps", "spread_bps"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")

    @property
    def total_bps(self) -> float:
        return self.fee_bps + self.slippage_bps + self.spread_bps

    def cost(self, turnover: float) -> float:
        """Cost as a fraction of equity, for a given absolute position change (0 to 2)."""
        if turnover < 0:
            raise ValueError("turnover must be non-negative")
        return turnover * self.total_bps / 10_000


ZERO_COST = TransactionCostModel(fee_bps=0.0, slippage_bps=0.0, spread_bps=0.0)
