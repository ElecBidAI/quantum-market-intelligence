"""Orchestration and synthesis (brief Section 16: "Chief Intelligence synthesizes the
final thesis").

`synthesize()` is the Chief Intelligence Agent: not a fifth analytical
lens, but a fixed aggregation rule over the other agents' opinions. A single
`VETO` (Risk Officer only, by construction — see risk_officer.py) makes the
thesis `VETO` unconditionally; the brief's "Risk Officer retains veto" is
enforced here exactly the same way risk_engine's own hard-reject tier
short-circuits everything after it. Otherwise the thesis is a
confidence-weighted average of every stance, so a confident dissent
outweighs a wishy-washy endorsement rather than every opinion counting
equally regardless of how sure it was.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ai_council.context import CouncilContext
from ai_council.opinion import AgentOpinion, Stance

STANCE_SCORES: dict[str, float] = {"SUPPORT": 1.0, "NEUTRAL": 0.0, "OPPOSE": -1.0}

SUPPORT_THRESHOLD = 0.3
OPPOSE_THRESHOLD = -0.3


class Agent(Protocol):
    agent_id: str

    def analyze(self, context: CouncilContext) -> AgentOpinion: ...


def run_council(agents: list[Agent], context: CouncilContext) -> list[AgentOpinion]:
    return [agent.analyze(context) for agent in agents]


@dataclass(frozen=True)
class ChiefIntelligenceThesis:
    final_stance: Stance
    weighted_score: float
    opinions: list[AgentOpinion]


def synthesize(
    opinions: list[AgentOpinion],
    support_threshold: float = SUPPORT_THRESHOLD,
    oppose_threshold: float = OPPOSE_THRESHOLD,
) -> ChiefIntelligenceThesis:
    if not opinions:
        raise ValueError("opinions must be non-empty")

    if any(o.stance == "VETO" for o in opinions):
        return ChiefIntelligenceThesis("VETO", weighted_score=-1.0, opinions=opinions)

    total_weight = sum(o.confidence for o in opinions)
    if total_weight == 0:
        weighted_score = 0.0
    else:
        numerator = sum(STANCE_SCORES[o.stance] * o.confidence for o in opinions)
        weighted_score = numerator / total_weight

    if weighted_score >= support_threshold:
        final: Stance = "SUPPORT"
    elif weighted_score <= oppose_threshold:
        final = "OPPOSE"
    else:
        final = "NEUTRAL"

    return ChiefIntelligenceThesis(final, weighted_score, opinions)
