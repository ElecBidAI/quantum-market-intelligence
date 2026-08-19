import pytest

from ai_council.agents.risk_officer import RiskOfficer


def test_approve_becomes_support(approve_decision, make_context):
    opinion = RiskOfficer().analyze(make_context(risk_decision=approve_decision()))
    assert opinion.stance == "SUPPORT"
    assert opinion.confidence == pytest.approx(1.0)


def test_reject_becomes_veto(reject_decision, make_context):
    opinion = RiskOfficer().analyze(make_context(risk_decision=reject_decision()))
    assert opinion.stance == "VETO"
    assert opinion.confidence == pytest.approx(1.0)
    assert opinion.findings[0].code == "MAX_DAILY_LOSS"


def test_reduce_becomes_neutral_with_confidence_reflecting_the_cut(reduce_decision, make_context):
    opinion = RiskOfficer().analyze(make_context(risk_decision=reduce_decision(adjustment=0.4)))
    assert opinion.stance == "NEUTRAL"
    assert opinion.confidence == pytest.approx(0.6)


def test_findings_mirror_the_risk_decisions_reasons(approve_decision, make_context):
    opinion = RiskOfficer().analyze(make_context(risk_decision=approve_decision()))
    assert opinion.findings[0].code == "OK"
    assert opinion.findings[0].detail == "within limits"
