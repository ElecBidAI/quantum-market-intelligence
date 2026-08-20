from datetime import UTC, datetime

from ai_council.db import fetch_recent_ohlcv, insert_narrative


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


def test_insert_narrative_issues_an_insert_with_expected_params():
    cursor = FakeCursor()
    insert_narrative(
        cursor,
        symbol="BTC-USDT",
        strategy_id="trend_following_sma_v1",
        regime="BULLISH_TREND",
        regime_confidence=0.9,
        decision="APPROVE",
        sizing_adjustment=None,
        final_stance="SUPPORT",
        weighted_score=1.0,
        narrative="some narrative text",
        candidate={"strategyId": "trend_following_sma_v1"},
        risk_decision={"decision": "APPROVE"},
        opinions=[{"agent_id": "quant_agent"}],
        timestamp="2026-08-19T00:00:00Z",
    )

    query, params = cursor.executed[0]
    assert "INSERT INTO council_narratives" in query
    assert params[0] == "BTC-USDT"
    assert params[1] == "trend_following_sma_v1"
    assert params[2] == "BULLISH_TREND"
    assert params[8] == "some narrative text"
    assert '"strategyId": "trend_following_sma_v1"' in params[9]
    assert '"decision": "APPROVE"' in params[10]
    assert '"agent_id": "quant_agent"' in params[11]
    assert params[12] == "2026-08-19T00:00:00Z"


def test_insert_narrative_no_candidate_branch_nulls_out_json_fields():
    cursor = FakeCursor()
    insert_narrative(
        cursor,
        symbol="BTC-USDT",
        strategy_id=None,
        regime="SIDEWAYS",
        regime_confidence=0.4,
        decision=None,
        sizing_adjustment=None,
        final_stance=None,
        weighted_score=None,
        narrative="no candidate for this regime",
        candidate=None,
        risk_decision=None,
        opinions=None,
        timestamp="2026-08-19T00:00:00Z",
    )

    _, params = cursor.executed[0]
    assert params[1] is None  # strategy_id
    assert params[9] is None  # candidate
    assert params[10] is None  # risk_decision
    assert params[11] is None  # opinions
