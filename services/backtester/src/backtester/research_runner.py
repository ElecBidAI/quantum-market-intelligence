"""Batch entry point: runs every configured strategy through the real
event-driven backtester (`engine.run_backtest`) against real ingested
OHLCV history for every configured symbol, and persists whatever it
computes to `backtests` (data/migrations/0004_backtests.sql).

Deliberately a one-shot batch job, not a daemon — same rationale as
services/ai-council/src/ai_council/run_pipeline.py: run it on a schedule
(cron, systemd timer, etc.) once there's an operational reason to pick a
cadence.

**Honest about small samples, not silently wrong.** A strategy/symbol pair
with too little real history to even classify a regime (fewer than
MIN_BARS_TO_RUN bars) is skipped entirely, logged, and produces no row —
never a fabricated one. For pairs that do run, any individual metric that's
mathematically undefined at the current sample size (e.g. a Sharpe ratio
with zero return variance, a profit factor with no losing trades yet) is
stored as `null` in `metrics`, not a fake placeholder number — callers must
treat an absent key as "not enough data for this stat yet," not zero.
`metrics["sampleSizeBars"]` and `metrics["numTrades"]` are always present
specifically so nothing downstream (the API, the UI) can display a number
without also knowing how much it should be trusted.

This is the first thing in this repository that runs `services/backtester`
against real Postgres-ingested bars instead of only synthetic test
fixtures — mirrors run_pipeline.py's own note about being the first real
run of the regime->strategy->risk chain.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime

import psycopg
from regime_engine.thresholds import RegimeThresholds
from strategy_engine.strategies import (
    BreakoutStrategy,
    MeanReversionStrategy,
    TrendFollowingStrategy,
)

from backtester.costs import TransactionCostModel
from backtester.db import fetch_all_ohlcv
from backtester.engine import BacktestResult, Bar, run_backtest
from backtester.metrics import (
    calmar_ratio,
    expectancy,
    payoff_ratio,
    profit_factor,
    recovery_factor,
    sharpe_ratio,
    sortino_ratio,
    turnover,
    win_rate,
)
from backtester.persistence import insert_backtest
from backtester.strategy_adapter import strategy_to_position_fn

# Mirrors ai_council.run_pipeline's Phase 1 universe (own small constant,
# not a cross-service import — same rule as everywhere else in this repo).
SYMBOLS = ["BTC-USDT", "ETH-USDT"]
INTERVAL = "1m"
VENUE = "binance"
MAX_BARS = 5000

# Headroom above regime_engine's own 50-bar (default thresholds) floor for
# classifying a regime at all — below this, a backtest would spend its
# entire walk unable to produce a single signal.
MIN_BARS_TO_RUN = 55

# Sharpe/Sortino/Calmar annualize per-period returns; 1-minute bars have
# this many periods per year.
PERIODS_PER_YEAR = 60 * 24 * 365

STRATEGIES = [TrendFollowingStrategy(), MeanReversionStrategy(), BreakoutStrategy()]
THRESHOLDS = RegimeThresholds()
COST_MODEL = TransactionCostModel()


def _safe(fn: Callable[..., float], *args: object) -> float | None:
    """Runs a metrics.py function, returning None instead of propagating a
    ValueError raised because the metric is mathematically undefined at
    the current sample size (see module docstring)."""
    try:
        return fn(*args)
    except ValueError:
        return None


def _compute_metrics(bars: list[Bar], result: BacktestResult) -> dict[str, object]:
    trades = result.round_trip_trade_returns
    return {
        "sampleSizeBars": len(bars),
        "numTrades": len(trades),
        "totalReturn": result.total_return,
        "turnover": turnover(result.positions_held),
        "winRate": _safe(win_rate, trades),
        "expectancy": _safe(expectancy, trades),
        "payoffRatio": _safe(payoff_ratio, trades),
        "profitFactor": _safe(profit_factor, trades),
        "sharpeRatio": _safe(sharpe_ratio, result.period_returns, PERIODS_PER_YEAR),
        "sortinoRatio": _safe(sortino_ratio, result.period_returns, PERIODS_PER_YEAR),
        "calmarRatio": _safe(calmar_ratio, result.equity_curve, PERIODS_PER_YEAR),
        "recoveryFactor": _safe(recovery_factor, result.equity_curve),
    }


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as conn, conn.cursor() as cursor:
        created_at = datetime.now(UTC).isoformat()

        for symbol in SYMBOLS:
            bars = fetch_all_ohlcv(cursor, symbol, INTERVAL, MAX_BARS)
            if len(bars) < MIN_BARS_TO_RUN:
                print(
                    f"[backtester] {symbol} {INTERVAL}: only {len(bars)} bars, "
                    f"need >= {MIN_BARS_TO_RUN}; skipping",
                    file=sys.stderr,
                )
                continue

            for strategy in STRATEGIES:
                position_fn = strategy_to_position_fn(strategy, symbol, VENUE, THRESHOLDS)
                result = run_backtest(bars, position_fn, COST_MODEL)
                metrics = _compute_metrics(bars, result)

                dataset_version = (
                    f"{symbol}:{INTERVAL}:{bars[0]['timestamp']}..{bars[-1]['timestamp']}:"
                    f"{len(bars)}bars"
                )

                # allowed_regimes is a frozenset (json-unserializable as-is);
                # every other strategy field is already a JSON-safe scalar.
                parameters = {
                    **asdict(strategy),
                    "allowed_regimes": sorted(strategy.allowed_regimes),
                }

                insert_backtest(
                    cursor,
                    strategy.strategy_id,
                    symbol,
                    INTERVAL,
                    dataset_version,
                    parameters,
                    asdict(COST_MODEL),
                    metrics,
                    created_at,
                )
                print(
                    f"[backtester] {strategy.strategy_id} {symbol}: "
                    f"{metrics['numTrades']} trade(s) over {metrics['sampleSizeBars']} bars"
                )

        conn.commit()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    run(database_url)


if __name__ == "__main__":
    main()
