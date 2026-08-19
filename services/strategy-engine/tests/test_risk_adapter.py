import pytest

from strategy_engine.risk_adapter import candidate_to_risk_request


def make_candidate(**overrides):
    defaults = dict(
        strategyId="trend_following_sma_v1",
        symbol="BTC-USDT",
        venue="binance",
        direction="LONG",
        horizon="4h",
        signalStrength=0.8,
        entryLogic={"entryPrice": 134.079731581767},
        invalidationLogic={},
        stopLogic={"stopPrice": 132.84470251933223},
        targetLogic={},
        expectedEdge=0.05,
        estimatedCosts=0.002,
        regime="BULLISH_TREND",
        timestamp="t59",
    )
    return {**defaults, **overrides}


def test_derives_stop_distance_pct_from_entry_and_stop_prices():
    candidate = make_candidate()
    request = candidate_to_risk_request(candidate, requested_size_pct=0.05)

    assert request.strategy_id == "trend_following_sma_v1"
    assert request.symbol == "BTC-USDT"
    assert request.direction == "LONG"
    assert request.requested_size_pct == pytest.approx(0.05)
    assert request.stop_distance_pct == pytest.approx(0.009211154048899581)


def test_stop_distance_is_none_when_entry_or_stop_price_is_missing():
    candidate = make_candidate(entryLogic={}, stopLogic={})
    request = candidate_to_risk_request(candidate, requested_size_pct=0.05)
    assert request.stop_distance_pct is None


def test_stop_distance_is_none_when_entry_price_is_zero():
    candidate = make_candidate(entryLogic={"entryPrice": 0}, stopLogic={"stopPrice": -5})
    request = candidate_to_risk_request(candidate, requested_size_pct=0.05)
    assert request.stop_distance_pct is None


def test_short_direction_passes_through_unchanged():
    candidate = make_candidate(direction="SHORT")
    request = candidate_to_risk_request(candidate, requested_size_pct=0.02)
    assert request.direction == "SHORT"
