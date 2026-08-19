"""Performance analytics on paper-traded results (brief Section 7).

Reuses `backtester.metrics` on `PositionBook.closed_trade_returns` — the
same win_rate/expectancy/payoff_ratio/profit_factor a backtest reports, now
computed on what was actually simulated as paper trades, so the two are
directly comparable (the whole point of paper trading being a checkpoint
before real capital: does live-ish behavior look like the backtest
promised?).

Each metric is computed independently and set to `None` — not omitted, not
zero — when the underlying `backtester.metrics` function raises (e.g.
`payoff_ratio` needs at least one win and one loss). A `None` here means
"not enough trades yet to compute this," never "zero edge."
"""

from __future__ import annotations

from collections.abc import Callable

from backtester.metrics import expectancy, payoff_ratio, profit_factor, win_rate


def _safe(fn: Callable[[list[float]], float], returns: list[float]) -> float | None:
    try:
        return fn(returns)
    except ValueError:
        return None


def summarize_trades(closed_trade_returns: list[float]) -> dict[str, float | int | None]:
    if not closed_trade_returns:
        return {
            "trade_count": 0,
            "win_rate": None,
            "expectancy": None,
            "payoff_ratio": None,
            "profit_factor": None,
        }

    return {
        "trade_count": len(closed_trade_returns),
        "win_rate": _safe(win_rate, closed_trade_returns),
        "expectancy": _safe(expectancy, closed_trade_returns),
        "payoff_ratio": _safe(payoff_ratio, closed_trade_returns),
        "profit_factor": _safe(profit_factor, closed_trade_returns),
    }
