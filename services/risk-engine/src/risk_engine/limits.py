"""Configurable hard limits (brief Section 9, "Hard controls").

These defaults are deliberately conservative placeholders, not researched,
validated risk parameters — see docs/risk/RISK-GOVERNANCE.md Section 5:
"Weights must be configurable and validated by strategy/regime" (the same
principle applies here). They exist so the engine is runnable and testable
now; whoever turns on paper trading for a real strategy must review and
justify every value before relying on it.

max_sector_exposure_pct is intentionally absent: crypto sector taxonomy
(e.g. "L1", "DeFi", "infra") isn't defined anywhere in this repository yet,
so a sector-exposure limit would have nothing real to check against.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    # Position / exposure limits, all expressed as a fraction of portfolio equity.
    max_position_pct: float = 0.10
    max_asset_exposure_pct: float = 0.10
    max_gross_exposure_pct: float = 1.0
    max_net_exposure_pct: float = 0.5
    max_leverage: float = 1.0

    # Loss / drawdown limits, expressed as positive fractions of equity.
    max_daily_loss_pct: float = 0.03
    max_weekly_loss_pct: float = 0.08
    max_portfolio_drawdown_pct: float = 0.20

    # Per-trade risk budget: caps position size so a stop-out risks no more
    # than this fraction of equity (see risk_engine.engine's use of
    # quant_core.risk.fixed_fractional_size).
    max_risk_per_trade_pct: float = 0.01

    # Portfolio-level VaR limit (optional gate; only checked when the caller
    # supplies portfolio_returns — see state.PortfolioState).
    max_portfolio_var_pct: float | None = 0.05
    var_confidence: float = 0.95

    # Liquidity / data-quality limits.
    max_spread_bps: float = 50.0
    max_data_age_seconds: float = 30.0  # matches services/market-data's STALE_THRESHOLD_MS

    def __post_init__(self) -> None:
        for field_name in (
            "max_position_pct",
            "max_asset_exposure_pct",
            "max_gross_exposure_pct",
            "max_net_exposure_pct",
            "max_leverage",
            "max_daily_loss_pct",
            "max_weekly_loss_pct",
            "max_portfolio_drawdown_pct",
            "max_risk_per_trade_pct",
            "max_spread_bps",
            "max_data_age_seconds",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.max_portfolio_var_pct is not None and self.max_portfolio_var_pct <= 0:
            raise ValueError("max_portfolio_var_pct must be positive when set")
        if not 0 < self.var_confidence < 1:
            raise ValueError("var_confidence must be between 0 and 1")
