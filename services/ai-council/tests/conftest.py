import pytest
from regime_engine.classify import RegimeResult

from ai_council.context import CouncilContext


def _make_candidate(**overrides):
    defaults = dict(
        strategyId="trend_following_sma_v1",
        symbol="BTC-USDT",
        venue="binance",
        direction="LONG",
        horizon="4h",
        signalStrength=0.8,
        entryLogic={"entryPrice": 100.0},
        invalidationLogic={},
        stopLogic={"stopPrice": 95.0},
        targetLogic={"targetPrice": 110.0},
        expectedEdge=0.05,
        estimatedCosts=0.01,
        regime="BULLISH_TREND",
        timestamp="2026-08-19T00:00:00Z",
    )
    return {**defaults, **overrides}


def _make_regime(label="BULLISH_TREND", confidence=0.9):
    return RegimeResult(label=label, confidence=confidence, metrics={})


def _approve_decision():
    return {
        "decision": "APPROVE",
        "reasons": [{"code": "OK", "detail": "within limits"}],
        "sizingAdjustment": None,
    }


def _reduce_decision(adjustment=0.5):
    return {
        "decision": "REDUCE",
        "reasons": [{"code": "MAX_POSITION", "detail": "capped"}],
        "sizingAdjustment": adjustment,
    }


def _reject_decision():
    return {
        "decision": "REJECT",
        "reasons": [{"code": "MAX_DAILY_LOSS", "detail": "breached"}],
        "sizingAdjustment": None,
    }


def _make_context(**overrides):
    defaults = dict(
        candidate=_make_candidate(),
        regime=_make_regime(),
        risk_decision=_approve_decision(),
    )
    return CouncilContext(**{**defaults, **overrides})


# Factory fixtures: pytest discovers conftest.py fixtures regardless of
# --import-mode (unlike `from conftest import ...`, which only works under
# the default "prepend" mode — a real bug caught when this suite was run
# alongside the rest of the workspace's tests under --import-mode=importlib).
@pytest.fixture
def make_candidate():
    return _make_candidate


@pytest.fixture
def make_regime():
    return _make_regime


@pytest.fixture
def approve_decision():
    return _approve_decision


@pytest.fixture
def reduce_decision():
    return _reduce_decision


@pytest.fixture
def reject_decision():
    return _reject_decision


@pytest.fixture
def make_context():
    return _make_context
