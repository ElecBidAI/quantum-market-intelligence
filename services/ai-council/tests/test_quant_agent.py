import pytest

from ai_council.agents.quant_agent import QuantAgent


def test_strong_edge_supports(make_candidate, make_context):
    # ratio = 0.01 / 0.005 = 2.0 exactly -> at the SUPPORT boundary
    candidate = make_candidate(expectedEdge=0.01, estimatedCosts=0.005)
    opinion = QuantAgent().analyze(make_context(candidate=candidate))
    assert opinion.stance == "SUPPORT"
    assert opinion.confidence == pytest.approx(0.5)


def test_thin_edge_is_neutral(make_candidate, make_context):
    # ratio = 0.005 / 0.005 = 1.0 -> at the NEUTRAL boundary
    candidate = make_candidate(expectedEdge=0.005, estimatedCosts=0.005)
    opinion = QuantAgent().analyze(make_context(candidate=candidate))
    assert opinion.stance == "NEUTRAL"
    assert opinion.confidence == pytest.approx(0.25)


def test_edge_below_costs_opposes(make_candidate, make_context):
    # ratio = 0.002 / 0.005 = 0.4
    candidate = make_candidate(expectedEdge=0.002, estimatedCosts=0.005)
    opinion = QuantAgent().analyze(make_context(candidate=candidate))
    assert opinion.stance == "OPPOSE"
    assert opinion.confidence == pytest.approx(0.1)
    assert any(f.code == "EDGE_DOES_NOT_COVER_COSTS" for f in opinion.findings)


def test_zero_cost_basis_is_neutral_with_zero_confidence(make_candidate, make_context):
    candidate = make_candidate(estimatedCosts=0.0)
    opinion = QuantAgent().analyze(make_context(candidate=candidate))
    assert opinion.stance == "NEUTRAL"
    assert opinion.confidence == pytest.approx(0.0)
    assert opinion.findings[0].code == "INVALID_COST_BASIS"


def test_confidence_saturates_at_one(make_candidate, make_context):
    candidate = make_candidate(expectedEdge=1.0, estimatedCosts=0.001)
    opinion = QuantAgent().analyze(make_context(candidate=candidate))
    assert opinion.confidence == pytest.approx(1.0)
