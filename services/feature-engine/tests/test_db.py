from datetime import UTC, datetime

from feature_engine.db import fetch_recent_ohlcv, upsert_features


class FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self._rows


def test_fetch_recent_ohlcv_reverses_desc_rows_to_ascending():
    rows = [
        (datetime(2026, 8, 19, 0, 2, tzinfo=UTC), 3, 3, 3, 3, 100),
        (datetime(2026, 8, 19, 0, 1, tzinfo=UTC), 2, 2, 2, 2, 100),
        (datetime(2026, 8, 19, 0, 0, tzinfo=UTC), 1, 1, 1, 1, 100),
    ]
    cursor = FakeCursor(rows)
    bars = fetch_recent_ohlcv(cursor, "BTC-USDT", "1m", limit=3)

    assert [b["close"] for b in bars] == [1, 2, 3]
    assert bars[0]["timestamp"] == "2026-08-19T00:00:00+00:00"


def test_fetch_recent_ohlcv_queries_with_symbol_interval_limit():
    cursor = FakeCursor([])
    fetch_recent_ohlcv(cursor, "ETH-USDT", "1m", limit=200)

    query, params = cursor.executed[0]
    assert "FROM ohlcv" in query
    assert "quality_status <> 'rejected'" in query
    assert params == ("ETH-USDT", "1m", 200)


def test_fetch_recent_ohlcv_empty_when_no_rows():
    cursor = FakeCursor([])
    assert fetch_recent_ohlcv(cursor, "BTC-USDT", "1m", limit=10) == []


def test_upsert_features_issues_an_upsert_with_expected_params():
    cursor = FakeCursor()
    upsert_features(
        cursor,
        symbol="BTC-USDT",
        interval="1m",
        feature_set="phase2-v1",
        schema_version=1,
        timestamp="2026-08-19T00:00:00Z",
        computed_at="2026-08-19T00:00:01Z",
        features={"last_close": 100},
    )

    query, params = cursor.executed[0]
    assert "INSERT INTO features" in query
    assert "ON CONFLICT (symbol, interval, feature_set" in query
    assert params[0] == "BTC-USDT"
    assert params[1] == "1m"
    assert params[2] == "phase2-v1"
    assert '"last_close": 100' in params[6]
