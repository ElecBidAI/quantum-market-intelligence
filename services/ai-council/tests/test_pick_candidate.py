from ai_council.run_pipeline import _pick_candidate


class FakeCursor:
    """Mimics fetch_latest_backtest_metrics' SQL usage: keyed on
    (strategy_id, symbol) captured from the last execute() call."""

    def __init__(self, metrics_by_key):
        self._metrics_by_key = metrics_by_key
        self._last_key = None

    def execute(self, query, params=None):
        self._last_key = (params[0], params[1])

    def fetchall(self):
        metrics = self._metrics_by_key.get(self._last_key)
        return [(metrics,)] if metrics is not None else []


def _candidate(strategy_id, expected_edge, symbol="BTC-USDT"):
    return {
        "strategyId": strategy_id,
        "symbol": symbol,
        "venue": "binance",
        "direction": "LONG",
        "horizon": "4h",
        "signalStrength": 0.5,
        "entryLogic": {},
        "invalidationLogic": {},
        "stopLogic": {},
        "targetLogic": {},
        "expectedEdge": expected_edge,
        "estimatedCosts": 0.002,
        "regime": "BULLISH_TREND",
        "timestamp": "2026-08-20T00:00:00Z",
    }


def test_no_candidates_returns_none_none():
    cursor = FakeCursor({})
    assert _pick_candidate([], cursor) == (None, None)


def test_falls_back_to_expected_edge_when_nothing_has_been_backtested():
    weak = _candidate("mean_reversion_bollinger_v1", expected_edge=0.02)
    strong = _candidate("breakout_donchian_v1", expected_edge=0.08)
    cursor = FakeCursor({})  # no backtests exist yet for either pair

    winner, backtested_sharpe = _pick_candidate([weak, strong], cursor)
    assert winner["strategyId"] == "breakout_donchian_v1"
    assert backtested_sharpe is None


def test_a_real_positive_backtested_sharpe_beats_a_higher_self_reported_edge():
    low_edge_but_proven = _candidate("trend_following_sma_v1", expected_edge=0.01)
    high_edge_but_unproven = _candidate("breakout_donchian_v1", expected_edge=0.20)
    cursor = FakeCursor(
        {
            ("trend_following_sma_v1", "BTC-USDT"): {"sharpeRatio": 1.5, "numTrades": 40},
            # breakout_donchian_v1 has no backtests row at all yet.
        }
    )

    winner, backtested_sharpe = _pick_candidate(
        [high_edge_but_unproven, low_edge_but_proven], cursor
    )
    assert winner["strategyId"] == "trend_following_sma_v1"
    assert backtested_sharpe == 1.5


def test_a_non_positive_backtested_sharpe_does_not_count_as_proven():
    losing_but_backtested = _candidate("mean_reversion_bollinger_v1", expected_edge=0.01)
    unbacktested_higher_edge = _candidate("breakout_donchian_v1", expected_edge=0.05)
    cursor = FakeCursor(
        {("mean_reversion_bollinger_v1", "BTC-USDT"): {"sharpeRatio": -0.4, "numTrades": 10}}
    )

    winner, backtested_sharpe = _pick_candidate(
        [losing_but_backtested, unbacktested_higher_edge], cursor
    )
    # Neither candidate qualifies as "proven"; falls back to expectedEdge.
    assert winner["strategyId"] == "breakout_donchian_v1"
    assert backtested_sharpe is None


def test_the_higher_of_two_real_positive_sharpes_wins():
    okay = _candidate("trend_following_sma_v1", expected_edge=0.01)
    better = _candidate("breakout_donchian_v1", expected_edge=0.01)
    cursor = FakeCursor(
        {
            ("trend_following_sma_v1", "BTC-USDT"): {"sharpeRatio": 0.8},
            ("breakout_donchian_v1", "BTC-USDT"): {"sharpeRatio": 2.1},
        }
    )

    winner, backtested_sharpe = _pick_candidate([okay, better], cursor)
    assert winner["strategyId"] == "breakout_donchian_v1"
    assert backtested_sharpe == 2.1
