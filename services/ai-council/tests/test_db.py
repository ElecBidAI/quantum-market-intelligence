from datetime import UTC, datetime

from ai_council.db import (
    fetch_all_fills,
    fetch_recent_ohlcv,
    insert_narrative,
    insert_risk_decision,
    insert_signal,
)


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
        narrative_en="some narrative text",
        narrative_es="algo de texto narrativo",
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
    assert params[9] == "algo de texto narrativo"
    assert '"strategyId": "trend_following_sma_v1"' in params[10]
    assert '"decision": "APPROVE"' in params[11]
    assert '"agent_id": "quant_agent"' in params[12]
    assert params[13] == "2026-08-19T00:00:00Z"


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
        narrative_en="no candidate for this regime",
        narrative_es="sin candidato para este régimen",
        candidate=None,
        risk_decision=None,
        opinions=None,
        timestamp="2026-08-19T00:00:00Z",
    )

    _, params = cursor.executed[0]
    assert params[1] is None  # strategy_id
    assert params[10] is None  # candidate
    assert params[11] is None  # risk_decision
    assert params[12] is None  # opinions


def test_insert_signal_issues_an_insert_with_expected_params():
    cursor = FakeCursor()
    candidate = {
        "strategyId": "trend_following_sma_v1",
        "symbol": "BTC-USDT",
        "venue": "binance",
        "direction": "LONG",
        "horizon": "4h",
        "signalStrength": 0.8,
        "entryLogic": {"entryPrice": 100.0},
        "invalidationLogic": {},
        "stopLogic": {"stopPrice": 95.0},
        "targetLogic": {"targetPrice": 110.0},
        "expectedEdge": 0.05,
        "estimatedCosts": 0.01,
        "regime": "BULLISH_TREND",
        "timestamp": "2026-08-19T00:00:00Z",
    }
    insert_signal(cursor, candidate)

    query, params = cursor.executed[0]
    assert "INSERT INTO signals" in query
    assert params[0] == "trend_following_sma_v1"
    assert params[1] == "BTC-USDT"
    assert params[3] == "LONG"
    assert '"entryPrice": 100.0' in params[6]
    assert params[12] == "BULLISH_TREND"
    assert params[13] == "2026-08-19T00:00:00Z"


def test_insert_risk_decision_issues_an_insert_with_expected_params():
    cursor = FakeCursor()
    decision = {
        "decision": "REDUCE",
        "strategyId": "trend_following_sma_v1",
        "reasons": [{"code": "MAX_POSITION", "detail": "capped"}],
        "sizingAdjustment": 0.5,
        "timestamp": "2026-08-19T00:00:00Z",
    }
    insert_risk_decision(cursor, decision, "BTC-USDT")

    query, params = cursor.executed[0]
    assert "INSERT INTO risk_decisions" in query
    assert params[0] == "REDUCE"
    assert params[1] == "trend_following_sma_v1"
    assert params[2] == "BTC-USDT"
    assert '"code": "MAX_POSITION"' in params[3]
    assert params[4] == 0.5
    assert params[5] == "2026-08-19T00:00:00Z"


def test_fetch_all_fills_orders_ascending_and_builds_fill_objects():
    rows = [
        ("order-1", "BTC-USDT", "LONG", 0.02, 65000.0, datetime(2026, 8, 19, 0, 0, tzinfo=UTC)),
        ("order-2", "ETH-USDT", "SHORT", 0.01, 3400.0, datetime(2026, 8, 19, 0, 1, tzinfo=UTC)),
    ]
    cursor = FakeCursor(rows)
    fills = fetch_all_fills(cursor)

    query, _ = cursor.executed[0]
    assert "FROM fills" in query
    assert "ORDER BY" in query

    assert len(fills) == 2
    assert fills[0].order_id == "order-1"
    assert fills[0].symbol == "BTC-USDT"
    assert fills[0].price == 65000.0
    assert fills[0].timestamp == "2026-08-19T00:00:00+00:00"
    assert fills[1].direction == "SHORT"


def test_fetch_all_fills_empty_when_no_rows():
    cursor = FakeCursor([])
    assert fetch_all_fills(cursor) == []
