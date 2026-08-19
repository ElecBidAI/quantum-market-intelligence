"""Event-driven backtester (brief Section 14).

The no-look-ahead guarantee is structural, not a rule the strategy has to
remember to follow: at step `t`, `strategy_fn` is called with
`bars[: t + 1]` — bars 0..t, inclusive of the just-closed bar t, and nothing
from bar t+1 onward. Whatever position it returns is deemed decided at the
close of bar t and is the position held over the return from bar t's close
to bar t+1's close. This is the standard discrete-time backtest convention:
"decide today, earn tomorrow's return."

Not implemented (documented, not silently assumed away):

- **Partial fills / capacity limits.** Every trade is assumed to fill in
  full at the bar's close-to-close return. A real limit-order-book fill
  simulator needs order-book depth over time, which
  data/migrations/0002_market_data.sql's `orderbook_snapshots` doesn't
  capture as a continuous history yet (Phase 1 only ingests periodic
  snapshots). Section 21's "partial-fill tests" are deferred with it.
- **Multi-asset / portfolio-level backtesting.** `bars` is a single
  symbol's OHLCV series; `strategy_fn` returns a single scalar position in
  [-1, 1]. Running several of these and combining them via
  `quant_core.portfolio` is possible today by hand, but there's no
  orchestration layer that does it for you.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypedDict

from backtester.costs import TransactionCostModel


class Bar(TypedDict):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


StrategyFn = Callable[[Sequence[Bar]], float]


@dataclass(frozen=True)
class TurnoverEvent:
    bar_index: int
    from_position: float
    to_position: float
    cost: float


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: list[float]
    positions_held: list[float]
    period_returns: list[float]
    turnover_events: list[TurnoverEvent]

    @property
    def total_return(self) -> float:
        return self.equity_curve[-1] / self.equity_curve[0] - 1

    @property
    def round_trip_trade_returns(self) -> list[float]:
        return extract_round_trip_trades(self.positions_held, self.equity_curve)


def extract_round_trip_trades(
    positions: Sequence[float], equity_curve: Sequence[float]
) -> list[float]:
    """Groups consecutive bars holding the same nonzero position into one trade's compounded return.

    A position change (including a direct sign flip, e.g. +1 to -1) always
    starts a new segment — a flip is two trades (close the long, open the
    short), never one.
    """
    if len(equity_curve) != len(positions) + 1:
        raise ValueError("equity_curve must have exactly one more entry than positions")

    period_returns = [
        equity_curve[i + 1] / equity_curve[i] - 1 for i in range(len(equity_curve) - 1)
    ]

    trades: list[float] = []
    segment_start = 0
    for i in range(1, len(positions) + 1):
        at_boundary = i == len(positions) or positions[i] != positions[segment_start]
        if at_boundary:
            if positions[segment_start] != 0:
                compounded = 1.0
                for r in period_returns[segment_start:i]:
                    compounded *= 1 + r
                trades.append(compounded - 1.0)
            segment_start = i
    return trades


def run_backtest(
    bars: Sequence[Bar],
    strategy_fn: StrategyFn,
    cost_model: TransactionCostModel,
    initial_equity: float = 1.0,
) -> BacktestResult:
    if len(bars) < 2:
        raise ValueError("need at least two bars to run a backtest")
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")

    closes = [b["close"] for b in bars]
    equity = initial_equity
    equity_curve = [equity]
    positions_held: list[float] = []
    period_returns: list[float] = []
    turnover_events: list[TurnoverEvent] = []
    position = 0.0

    for t in range(len(bars) - 1):
        signal = strategy_fn(bars[: t + 1])
        if not -1.0 <= signal <= 1.0:
            raise ValueError(f"strategy_fn must return a position in [-1, 1], got {signal}")

        bar_return = (closes[t + 1] - closes[t]) / closes[t]
        turnover = abs(signal - position)
        cost = cost_model.cost(turnover)
        pnl = signal * bar_return

        equity = equity * (1 + pnl) * (1 - cost)
        equity_curve.append(equity)
        positions_held.append(signal)
        period_returns.append(equity_curve[-1] / equity_curve[-2] - 1)

        if turnover > 0:
            event = TurnoverEvent(
                bar_index=t + 1, from_position=position, to_position=signal, cost=cost
            )
            turnover_events.append(event)
        position = signal

    return BacktestResult(
        equity_curve=equity_curve,
        positions_held=positions_held,
        period_returns=period_returns,
        turnover_events=turnover_events,
    )
