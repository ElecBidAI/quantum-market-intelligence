"""An agent's structured output — never free text (brief Section 24: "do not treat AI text
output as a market signal"). Every opinion is a stance plus machine-readable findings, the
same reason-code discipline `risk_engine.engine` uses for its decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Stance = Literal["SUPPORT", "OPPOSE", "NEUTRAL", "VETO"]


@dataclass(frozen=True)
class Finding:
    code: str
    detail: str


@dataclass(frozen=True)
class AgentOpinion:
    agent_id: str
    stance: Stance
    confidence: float
    findings: list[Finding] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
