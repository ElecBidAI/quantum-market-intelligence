"""Postgres access for backtester, kept thin and injectable for tests.

Same shape as services/ai-council/src/ai_council/db.py's `Cursor` Protocol:
any object exposing `.execute(sql, params)` and `.fetchall()` the way a
psycopg cursor does will work here. Not imported from ai_council — services
only share state through Postgres, not code, same rule applied everywhere
else in this repository.
"""

from __future__ import annotations

from typing import Protocol

from backtester.engine import Bar


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = ...) -> object: ...
    def fetchall(self) -> list[tuple[object, ...]]: ...


def fetch_all_ohlcv(cursor: Cursor, symbol: str, interval: str, limit: int = 5000) -> list[Bar]:
    """Fetches up to `limit` most recent non-rejected closed bars, oldest first.

    Unlike ai_council.db.fetch_recent_ohlcv (which bounds itself to a small
    live-pipeline lookback), this is meant to pull as much real history as
    exists for a research backtest — `limit` is a sanity cap, not a tuning
    knob callers are expected to tighten.
    """
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
    return list(reversed(bars))  # DESC query -> reverse to ascending
