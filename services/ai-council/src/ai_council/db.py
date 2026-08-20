"""Postgres access for ai-council, kept thin and injectable for tests.

Any object exposing `.execute(sql, params)` and `.fetchall()` the way a
psycopg cursor does will work here — tests pass a fake, run_narrative.py
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
    narrative: str,
    candidate: dict | None,
    risk_decision: dict | None,
    opinions: list[dict] | None,
    timestamp: str,
) -> None:
    """Appends one row. Never an upsert — council_narratives is append-only,
    same policy as risk_decisions (data/migrations/0001_init.sql)."""
    cursor.execute(
        """
        INSERT INTO council_narratives
            (symbol, strategy_id, regime, regime_confidence, decision, sizing_adjustment,
             final_stance, weighted_score, narrative, candidate, risk_decision, opinions,
             "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            narrative,
            json.dumps(candidate) if candidate is not None else None,
            json.dumps(risk_decision) if risk_decision is not None else None,
            json.dumps(opinions) if opinions is not None else None,
            timestamp,
        ),
    )
