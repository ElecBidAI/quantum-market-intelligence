from strategy_engine.persistence import insert_signal


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


def test_insert_signal_issues_expected_sql_and_params():
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
        "stopLogic": {"stopPrice": 98.0},
        "targetLogic": {"targetPrice": 104.0},
        "expectedEdge": 0.05,
        "estimatedCosts": 0.002,
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
