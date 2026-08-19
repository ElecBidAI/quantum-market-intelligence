"""Inputs to a risk evaluation.

These are the engine's own request/state shapes, not `packages/contracts`
TS types — Python and TypeScript have no shared-type mechanism in this
repo, so the boundary is the JSON produced by RiskDecision.to_contract()
(engine.py), which is kept structurally identical to
packages/contracts/src/risk.ts's `riskDecision` schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateRequest:
    """The sizing-relevant subset of a strategy candidate (packages/contracts's StrategyCandidate).

    `requested_size_pct` is how much of equity the candidate wants to
    allocate, as a positive fraction; `direction` supplies the sign.
    `stop_distance_pct`, when known, is the distance from entry to stop as a
    fraction of entry price — used to cap size via the per-trade risk budget
    (RiskLimits.max_risk_per_trade_pct).
    """

    strategy_id: str
    symbol: str
    direction: str  # "LONG" | "SHORT" | "NEUTRAL"
    requested_size_pct: float
    stop_distance_pct: float | None = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT", "NEUTRAL"):
            raise ValueError('direction must be "LONG", "SHORT", or "NEUTRAL"')
        if self.requested_size_pct <= 0:
            raise ValueError("requested_size_pct must be positive")
        if self.stop_distance_pct is not None and self.stop_distance_pct <= 0:
            raise ValueError("stop_distance_pct must be positive when set")


@dataclass(frozen=True)
class PortfolioState:
    """Current portfolio state, all figures as fractions of equity."""

    equity: float
    # signed exposure per symbol, e.g. {"BTC-USDT": 0.08, "ETH-USDT": -0.03}
    position_pct_by_symbol: dict[str, float] = field(default_factory=dict)
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    # optional: recent portfolio-level returns, for the VaR gate (RiskLimits.max_portfolio_var_pct)
    portfolio_returns: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.equity <= 0:
            raise ValueError("equity must be positive")
        if self.current_drawdown_pct < 0:
            raise ValueError("current_drawdown_pct must be non-negative")

    @property
    def gross_exposure_pct(self) -> float:
        return sum(abs(v) for v in self.position_pct_by_symbol.values())

    @property
    def net_exposure_pct(self) -> float:
        return sum(self.position_pct_by_symbol.values())

    def position_pct(self, symbol: str) -> float:
        return self.position_pct_by_symbol.get(symbol, 0.0)


@dataclass(frozen=True)
class MarketContext:
    """Market-quality inputs the engine needs to enforce liquidity/staleness limits."""

    spread_bps: float
    data_age_seconds: float
    kill_switch_engaged: bool = False
    circuit_breaker_engaged: bool = False

    def __post_init__(self) -> None:
        if self.spread_bps < 0:
            raise ValueError("spread_bps must be non-negative")
        if self.data_age_seconds < 0:
            raise ValueError("data_age_seconds must be non-negative")
