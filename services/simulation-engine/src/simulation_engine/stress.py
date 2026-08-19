"""Stress scenarios (brief Section 13).

Only the scenarios expressible as a direct transform of a price, a return
series, or a cost model are implemented:

- price shock (-10/-20/-40%)
- volatility multiplier (x2/x3)
- spread/cost multiplier (x5/x10), via backtester.costs.TransactionCostModel

The narrative scenarios — exchange outage, extreme funding, liquidation
cascade, correlation convergence, stablecoin depeg, hack/regulatory event —
are not implemented. Each needs data or a model this repository doesn't have
yet: liquidation cascade needs leverage/liquidation-price data (no
derivatives ingestion — services/market-data is spot-only, Phase 9 territory
per the brief); correlation convergence needs a live multi-asset covariance
estimator (there's no forecast-engine to supply one); stablecoin depeg and
exchange outage are single-event narratives that would need bespoke
scenario logic, not a reusable formula. Treating any of these as "just
multiply something by a number" would misrepresent what actually happens in
those events, which is worse than leaving them undocumented gaps.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from backtester.costs import TransactionCostModel

# Named after the brief's own scenario list (Section 13) so a caller can
# cite exactly which one they ran.
PRICE_SHOCK_SCENARIOS = {
    "price_shock_-10pct": -0.10,
    "price_shock_-20pct": -0.20,
    "price_shock_-40pct": -0.40,
}
VOLATILITY_SCENARIOS = {"volatility_x2": 2.0, "volatility_x3": 3.0}
SPREAD_SCENARIOS = {"spread_x5": 5.0, "spread_x10": 10.0}


def apply_price_shock(price: float, shock_pct: float) -> float:
    """A single instantaneous price move, e.g. shock_pct=-0.20 for a 20% drop."""
    if price <= 0:
        raise ValueError("price must be positive")
    if shock_pct <= -1:
        raise ValueError("shock_pct must be > -1 (a price cannot go to zero or below)")
    return price * (1 + shock_pct)


def apply_volatility_multiplier(returns: Sequence[float], multiplier: float) -> np.ndarray:
    """Scales each return's deviation from the series mean by `multiplier`, preserving the mean."""
    if multiplier < 0:
        raise ValueError("multiplier must be non-negative")
    arr = np.asarray(returns, dtype=float)
    if arr.size == 0:
        raise ValueError("returns must be non-empty")
    mean = arr.mean()
    return mean + (arr - mean) * multiplier


def stressed_cost_model(
    base: TransactionCostModel, spread_multiplier: float
) -> TransactionCostModel:
    """Widens `spread_bps` for a stress scenario; fee_bps and slippage_bps are left unchanged."""
    if spread_multiplier < 1:
        raise ValueError("spread_multiplier must be >= 1 for a stress scenario")
    return TransactionCostModel(
        fee_bps=base.fee_bps,
        slippage_bps=base.slippage_bps,
        spread_bps=base.spread_bps * spread_multiplier,
    )


@dataclass(frozen=True)
class StressTestResult:
    scenario_name: str
    baseline_value: float
    stressed_value: float

    @property
    def impact(self) -> float:
        return self.stressed_value - self.baseline_value

    @property
    def impact_pct(self) -> float:
        if self.baseline_value == 0:
            raise ValueError("baseline_value is zero; impact_pct is undefined")
        return self.impact / abs(self.baseline_value)


def run_price_shock_scenario(scenario_name: str, price: float) -> StressTestResult:
    if scenario_name not in PRICE_SHOCK_SCENARIOS:
        known = list(PRICE_SHOCK_SCENARIOS)
        raise ValueError(f"unknown price shock scenario {scenario_name!r}; known: {known}")
    shocked = apply_price_shock(price, PRICE_SHOCK_SCENARIOS[scenario_name])
    return StressTestResult(
        scenario_name=scenario_name, baseline_value=price, stressed_value=shocked
    )
