"""Postgres access for feature-engine, kept thin and injectable for tests.

Any object exposing `.execute(sql, params)` and `.fetchall()`/`.fetchone()`
the way a psycopg cursor does will work here — tests pass a fake, main.py
passes a real psycopg cursor.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from feature_engine.features import Bar


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
    return list(reversed(bars))  # DESC query -> reverse to ascending for compute_features


def upsert_features(
    cursor: Cursor,
    symbol: str,
    interval: str,
    feature_set: str,
    schema_version: int,
    timestamp: str,
    computed_at: str,
    features: dict[str, object],
) -> None:
    """Upserts one feature row, keyed by (symbol, interval, feature_set, timestamp)."""
    cursor.execute(
        """
        INSERT INTO features
            (symbol, interval, feature_set, "timestamp", computed_at, schema_version, features)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, interval, feature_set, "timestamp")
        DO UPDATE SET features = EXCLUDED.features, computed_at = EXCLUDED.computed_at
        """,
        (
            symbol,
            interval,
            feature_set,
            timestamp,
            computed_at,
            schema_version,
            json.dumps(features),
        ),
    )
