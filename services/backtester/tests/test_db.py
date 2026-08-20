from datetime import UTC, datetime

from backtester.db import fetch_all_ohlcv


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self._rows


def test_fetch_all_ohlcv_reverses_desc_rows_to_ascending():
    rows = [
        (datetime(2026, 8, 19, 0, 2, tzinfo=UTC), 3, 3, 3, 3, 100),
        (datetime(2026, 8, 19, 0, 1, tzinfo=UTC), 2, 2, 2, 2, 100),
        (datetime(2026, 8, 19, 0, 0, tzinfo=UTC), 1, 1, 1, 1, 100),
    ]
    cursor = FakeCursor(rows)
    bars = fetch_all_ohlcv(cursor, "BTC-USDT", "1m", limit=3)

    assert [b["close"] for b in bars] == [1, 2, 3]
    assert bars[0]["timestamp"] == "2026-08-19T00:00:00+00:00"


def test_fetch_all_ohlcv_queries_with_symbol_interval_limit():
    cursor = FakeCursor([])
    fetch_all_ohlcv(cursor, "ETH-USDT", "1m", limit=5000)

    query, params = cursor.executed[0]
    assert "FROM ohlcv" in query
    assert "quality_status <> 'rejected'" in query
    assert params == ("ETH-USDT", "1m", 5000)


def test_fetch_all_ohlcv_empty_when_no_rows():
    cursor = FakeCursor([])
    assert fetch_all_ohlcv(cursor, "BTC-USDT", "1m") == []


def test_fetch_all_ohlcv_defaults_limit_to_5000():
    cursor = FakeCursor([])
    fetch_all_ohlcv(cursor, "BTC-USDT", "1m")

    _, params = cursor.executed[0]
    assert params[2] == 5000
