"""The Risk Officer's opinion IS risk_engine's decision, translated — never re-derived.

Brief Section 16: "Risk Officer retains veto." This agent doesn't run its
own risk analysis (that would risk disagreeing with the actual gate,
which would be nonsensical — risk_engine.evaluate() already is the
authority docs/risk/RISK-GOVERNANCE.md establishes). REJECT becomes VETO,
unconditionally overriding council.synthesize()'s otherwise-weighted vote.
"""

from __future__ import annotations

from ai_council.context import CouncilContext
from ai_council.opinion import AgentOpinion, Finding


class RiskOfficer:
    agent_id = "risk_officer"

    def analyze(self, context: CouncilContext) -> AgentOpinion:
        decision = context.risk_decision
        findings = [Finding(r["code"], r["detail"]) for r in decision["reasons"]]

        if decision["decision"] == "REJECT":
            return AgentOpinion(self.agent_id, "VETO", 1.0, findings)

        if decision["decision"] == "REDUCE":
            adjustment = decision["sizingAdjustment"]
            confidence = 1.0 - adjustment  # a bigger cut signals more caution
            return AgentOpinion(self.agent_id, "NEUTRAL", confidence, findings)

        return AgentOpinion(self.agent_id, "SUPPORT", 1.0, findings)
