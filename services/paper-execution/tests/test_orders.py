import pytest

from paper_execution.orders import create_order_from_decision


def make_candidate(**overrides):
    defaults = dict(
        strategyId="trend_following_sma_v1",
        symbol="BTC-USDT",
        direction="LONG",
        timestamp="2026-08-19T00:00:00Z",
    )
    return {**defaults, **overrides}


def approve_decision():
    return {
        "decision": "APPROVE",
        "reasons": [{"code": "OK", "detail": "..."}],
        "sizingAdjustment": None,
    }


def reduce_decision(adjustment=0.5):
    return {
        "decision": "REDUCE",
        "reasons": [{"code": "MAX_POSITION", "detail": "..."}],
        "sizingAdjustment": adjustment,
    }


def reject_decision():
    return {
        "decision": "REJECT",
        "reasons": [{"code": "MAX_DAILY_LOSS", "detail": "..."}],
        "sizingAdjustment": None,
    }


def test_approve_creates_an_order_at_full_requested_size():
    order = create_order_from_decision(
        make_candidate(), approve_decision(), requested_size_pct=0.05
    )
    assert order.size_pct == pytest.approx(0.05)
    assert order.risk_decision_code == "APPROVE"
    assert order.strategy_id == "trend_following_sma_v1"
    assert order.symbol == "BTC-USDT"
    assert order.direction == "LONG"
    assert order.order_id  # non-empty


def test_reduce_creates_an_order_scaled_by_sizing_adjustment():
    order = create_order_from_decision(
        make_candidate(), reduce_decision(adjustment=0.4), requested_size_pct=0.10
    )
    assert order.size_pct == pytest.approx(0.04)
    assert order.risk_decision_code == "REDUCE"


def test_reject_never_produces_an_order():
    with pytest.raises(ValueError, match="REJECT"):
        create_order_from_decision(make_candidate(), reject_decision(), requested_size_pct=0.05)


def test_reduce_without_sizing_adjustment_is_rejected():
    broken_decision = {"decision": "REDUCE", "reasons": [], "sizingAdjustment": None}
    with pytest.raises(ValueError):
        create_order_from_decision(make_candidate(), broken_decision, requested_size_pct=0.05)


def test_rejects_non_positive_requested_size():
    with pytest.raises(ValueError):
        create_order_from_decision(make_candidate(), approve_decision(), requested_size_pct=0)


def test_order_id_is_injectable_for_deterministic_tests():
    order = create_order_from_decision(
        make_candidate(), approve_decision(), requested_size_pct=0.05, order_id="fixed-id"
    )
    assert order.order_id == "fixed-id"
