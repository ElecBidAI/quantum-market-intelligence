import pytest

from ai_council.council import run_council, synthesize
from ai_council.opinion import AgentOpinion


class FakeAgent:
    def __init__(self, agent_id, stance, confidence):
        self.agent_id = agent_id
        self._stance = stance
        self._confidence = confidence

    def analyze(self, context):
        return AgentOpinion(self.agent_id, self._stance, self._confidence, [])


def test_run_council_calls_every_agent(make_context):
    agents = [FakeAgent("a", "SUPPORT", 0.5), FakeAgent("b", "OPPOSE", 0.5)]
    opinions = run_council(agents, make_context())
    assert [o.agent_id for o in opinions] == ["a", "b"]


def test_synthesize_unanimous_support():
    opinions = [
        AgentOpinion("a", "SUPPORT", 0.8, []),
        AgentOpinion("b", "SUPPORT", 1.0, []),
        AgentOpinion("c", "SUPPORT", 1.0, []),
    ]
    thesis = synthesize(opinions)
    assert thesis.final_stance == "SUPPORT"
    assert thesis.weighted_score == pytest.approx(1.0)


def test_synthesize_known_weighted_value():
    # (1*0.8 + 1*1.0 + 0*0.0 + 1*1.0) / (0.8+1.0+0.0+1.0) = 2.8/2.8 = 1.0
    opinions = [
        AgentOpinion("quant", "SUPPORT", 0.8, []),
        AgentOpinion("risk_officer", "SUPPORT", 1.0, []),
        AgentOpinion("devils_advocate", "NEUTRAL", 0.0, []),
        AgentOpinion("auditor", "SUPPORT", 1.0, []),
    ]
    thesis = synthesize(opinions)
    assert thesis.weighted_score == pytest.approx(1.0)
    assert thesis.final_stance == "SUPPORT"


def test_a_single_veto_overrides_every_other_opinion():
    opinions = [
        AgentOpinion("quant", "SUPPORT", 1.0, []),
        AgentOpinion("risk_officer", "VETO", 1.0, []),
        AgentOpinion("auditor", "SUPPORT", 1.0, []),
    ]
    thesis = synthesize(opinions)
    assert thesis.final_stance == "VETO"


def test_confident_dissent_outweighs_a_wishy_washy_endorsement():
    opinions = [
        AgentOpinion("a", "SUPPORT", 0.1, []),  # barely-confident support
        AgentOpinion("b", "OPPOSE", 1.0, []),  # fully-confident opposition
    ]
    thesis = synthesize(opinions)
    # (1*0.1 + -1*1.0) / (0.1+1.0) = -0.9/1.1 = -0.818...
    assert thesis.weighted_score == pytest.approx(-0.8181818181818182)
    assert thesis.final_stance == "OPPOSE"


def test_mixed_opinions_near_zero_are_neutral():
    opinions = [AgentOpinion("a", "SUPPORT", 0.3, []), AgentOpinion("b", "OPPOSE", 0.3, [])]
    thesis = synthesize(opinions)
    assert thesis.weighted_score == pytest.approx(0.0)
    assert thesis.final_stance == "NEUTRAL"


def test_all_zero_confidence_is_neutral_not_a_division_error():
    opinions = [AgentOpinion("a", "SUPPORT", 0.0, []), AgentOpinion("b", "OPPOSE", 0.0, [])]
    thesis = synthesize(opinions)
    assert thesis.weighted_score == pytest.approx(0.0)
    assert thesis.final_stance == "NEUTRAL"


def test_synthesize_rejects_empty_opinions():
    with pytest.raises(ValueError):
        synthesize([])


def test_end_to_end_council_with_real_agents_reject_decision(make_context, reject_decision):
    from ai_council.agents import Auditor, DevilsAdvocate, QuantAgent, RiskOfficer

    context = make_context(risk_decision=reject_decision())
    opinions = run_council([QuantAgent(), RiskOfficer(), DevilsAdvocate(), Auditor()], context)
    thesis = synthesize(opinions)
    assert thesis.final_stance == "VETO"


def test_end_to_end_council_with_real_agents_reduce_decision(make_context, reduce_decision):
    from ai_council.agents import Auditor, DevilsAdvocate, QuantAgent, RiskOfficer

    context = make_context(risk_decision=reduce_decision(adjustment=0.9))
    opinions = run_council([QuantAgent(), RiskOfficer(), DevilsAdvocate(), Auditor()], context)
    thesis = synthesize(opinions)
    assert thesis.final_stance != "VETO"
    assert all(o.stance != "VETO" for o in opinions if o.agent_id != "risk_officer")
