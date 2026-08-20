import pytest
from regime_engine.classify import RegimeResult

from ai_council.context import CouncilContext
from ai_council.council import ChiefIntelligenceThesis
from ai_council.opinion import AgentOpinion


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


def _make_opinions(**overrides):
    """One opinion per real agent, all fully aligned SUPPORT by default (DevilsAdvocate
    can never SUPPORT by construction, so its default is a clean NEUTRAL/no-findings)."""
    defaults = dict(
        quant_agent=AgentOpinion("quant_agent", "SUPPORT", 0.9, []),
        risk_officer=AgentOpinion("risk_officer", "SUPPORT", 1.0, []),
        devils_advocate=AgentOpinion("devils_advocate", "NEUTRAL", 0.0, []),
        auditor_agent=AgentOpinion("auditor_agent", "SUPPORT", 1.0, []),
    )
    return list({**defaults, **overrides}.values())


def _make_thesis(opinions=None, final_stance="SUPPORT", weighted_score=1.0):
    return ChiefIntelligenceThesis(
        final_stance, weighted_score, opinions if opinions is not None else _make_opinions()
    )


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


@pytest.fixture
def make_opinions():
    return _make_opinions


@pytest.fixture
def make_thesis():
    return _make_thesis
