"""Postgres access for ai-council, kept thin and injectable for tests.

Any object exposing `.execute(sql, params)` and `.fetchall()` the way a
psycopg cursor does will work here — tests pass a fake, run_pipeline.py
passes a real psycopg cursor. Mirrors
services/feature-engine/src/feature_engine/db.py's shape exactly; not
imported from there — services only share state through Postgres, not
code (the same rule already applied on the TS side between
services/market-data and apps/api).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from paper_execution.fills import Fill
from regime_engine.classify import Bar


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = ...) -> object: ...
    def fetchall(self) -> list[tuple[object, ...]]: ...


def fetch_recent_ohlcv(cursor: Cursor, symbol: str, interval: str, limit: int) -> list[Bar]:
    """Fetches the most recent `limit` non-rejected closed bars, oldest first."""
    cursor.execute(
        """
        SELECT "timestamp", open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = %s AND interval = %s AND quality_status <> 'rejected'
        ORDER BY "timestamp" DESC
        LIMIT %s
        """,
        (symbol, interval, limit),
    )
    rows = cursor.fetchall()
    bars = [
        Bar(
            timestamp=row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            open=row[1],
            high=row[2],
            low=row[3],
            close=row[4],
            volume=row[5],
        )
        for row in rows
    ]
    return list(reversed(bars))  # DESC query -> reverse to ascending for classify_regime


def insert_narrative(
    cursor: Cursor,
    *,
    symbol: str,
    strategy_id: str | None,
    regime: str,
    regime_confidence: float,
    decision: str | None,
    sizing_adjustment: float | None,
    final_stance: str | None,
    weighted_score: float | None,
    narrative_en: str,
    narrative_es: str,
    candidate: dict | None,
    risk_decision: dict | None,
    opinions: list[dict] | None,
    timestamp: str,
) -> None:
    """Appends one row. Never an upsert — council_narratives is append-only,
    same policy as risk_decisions (data/migrations/0001_init.sql).

    Both language renders are required — see
    ai_council.narrator's module docstring: run_pipeline.py always calls
    `generate_narrative` twice (language="en" and "es") against the same
    pipeline output before persisting, so there's never a row with only
    one language present.
    """
    cursor.execute(
        """
        INSERT INTO council_narratives
            (symbol, strategy_id, regime, regime_confidence, decision, sizing_adjustment,
             final_stance, weighted_score, narrative_en, narrative_es, candidate,
             risk_decision, opinions, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            symbol,
            strategy_id,
            regime,
            regime_confidence,
            decision,
            sizing_adjustment,
            final_stance,
            weighted_score,
            narrative_en,
            narrative_es,
            json.dumps(candidate) if candidate is not None else None,
            json.dumps(risk_decision) if risk_decision is not None else None,
            json.dumps(opinions) if opinions is not None else None,
            timestamp,
        ),
    )


def insert_signal(cursor: Cursor, candidate: dict) -> None:
    """Appends one row to `signals` (data/migrations/0001_init.sql) —
    mirrors packages/contracts/src/strategy.ts's `strategyCandidate`
    field-for-field. Append-only, never an upsert, same policy as every
    other table this module writes."""
    cursor.execute(
        """
        INSERT INTO signals
            (strategy_id, symbol, venue, direction, horizon, signal_strength,
             entry_logic, invalidation_logic, stop_logic, target_logic,
             expected_edge, estimated_costs, regime, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            candidate["strategyId"],
            candidate["symbol"],
            candidate["venue"],
            candidate["direction"],
            candidate["horizon"],
            candidate["signalStrength"],
            json.dumps(candidate["entryLogic"]),
            json.dumps(candidate["invalidationLogic"]),
            json.dumps(candidate["stopLogic"]),
            json.dumps(candidate["targetLogic"]),
            candidate["expectedEdge"],
            candidate["estimatedCosts"],
            candidate["regime"],
            candidate["timestamp"],
        ),
    )


def insert_risk_decision(cursor: Cursor, decision: dict, symbol: str) -> None:
    """Appends one row to `risk_decisions` — immutable/append-only by
    policy (data/migrations/0001_init.sql's own comment: corrections are
    new rows, never UPDATEs).

    `symbol` is not a field on `decision` itself (risk_engine's decision
    dict, and packages/contracts/src/risk.ts's `riskDecision` schema it
    mirrors, have no symbol field) — the caller must supply it. Without it,
    a signal's risk decision can only be correlated by strategy_id +
    timestamp, which is ambiguous whenever two symbols pick the same
    strategy in the same run with bars sharing a last-bar timestamp
    (data/migrations/0011_risk_decisions_symbol.sql's own comment has the
    real example this was caught from)."""
    cursor.execute(
        """
        INSERT INTO risk_decisions
            (decision, strategy_id, symbol, reasons, sizing_adjustment, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            decision["decision"],
            decision["strategyId"],
            symbol,
            json.dumps(decision["reasons"]),
            decision["sizingAdjustment"],
            decision["timestamp"],
        ),
    )


def fetch_latest_backtest_metrics(
    cursor: Cursor, strategy_id: str, symbol: str
) -> dict[str, object] | None:
    """Reads the latest `backtests.metrics` JSONB for one (strategy, symbol)
    pair (data/migrations/0004_backtests.sql, written by
    `python -m backtester.research_runner`). `None` if that pair hasn't
    been backtested yet — an honest "no track record yet," not a
    fabricated zero — see `run_pipeline._pick_candidate`, the only caller,
    for how that's handled."""
    cursor.execute(
        """
        SELECT metrics
        FROM backtests
        WHERE strategy_id = %s AND symbol = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (strategy_id, symbol),
    )
    row = cursor.fetchall()
    if not row:
        return None
    metrics = row[0][0]
    return metrics if isinstance(metrics, dict) else json.loads(metrics)


def fetch_all_fills(cursor: Cursor) -> list[Fill]:
    """Fetches every fill ever recorded, oldest first — the full ledger
    `paper_execution.positions.replay_positions` needs to reconstruct the
    current PositionBook from scratch. There is no persisted in-memory
    book across runs (see run_pipeline.py's module docstring), so this
    read happens once at the start of every run."""
    cursor.execute(
        """
        SELECT order_id, symbol, direction, size_pct, price, "timestamp"
        FROM fills
        ORDER BY "timestamp" ASC
        """
    )
    rows = cursor.fetchall()
    return [
        Fill(
            order_id=row[0],
            symbol=row[1],
            direction=row[2],
            size_pct=row[3],
            price=row[4],
            timestamp=row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
        )
        for row in rows
    ]
