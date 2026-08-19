"""Checks whether the candidate's own claimed edge clears its own claimed costs.

`expectedEdge` and `estimatedCosts` are naive placeholders on every strategy
in `services/strategy-engine` today (see those strategies' docstrings) — this
agent audits the ratio between them, it doesn't invent a better edge
estimate. A high ratio here means "internally consistent," not "actually
profitable"; only a real backtest (services/backtester) can claim that.
"""

from __future__ import annotations

from ai_council.context import CouncilContext
from ai_council.opinion import AgentOpinion, Finding

SUPPORT_RATIO = 2.0
NEUTRAL_RATIO = 1.0


class QuantAgent:
    agent_id = "quant_agent"

    def analyze(self, context: CouncilContext) -> AgentOpinion:
        candidate = context.candidate
        costs = candidate["estimatedCosts"]
        edge = candidate["expectedEdge"]

        if costs <= 0:
            detail = f"estimatedCosts must be positive, got {costs}"
            findings = [Finding("INVALID_COST_BASIS", detail)]
            return AgentOpinion(self.agent_id, "NEUTRAL", 0.0, findings)

        ratio = edge / costs
        findings = [Finding("EDGE_TO_COST_RATIO", f"expectedEdge/estimatedCosts = {ratio:.2f}")]

        if ratio >= SUPPORT_RATIO:
            stance = "SUPPORT"
        elif ratio >= NEUTRAL_RATIO:
            stance = "NEUTRAL"
        else:
            stance = "OPPOSE"
            findings.append(
                Finding("EDGE_DOES_NOT_COVER_COSTS", f"ratio {ratio:.2f} < {NEUTRAL_RATIO}")
            )

        # 0.5 at the SUPPORT threshold, 1.0 at 2x it — same confidence convention
        # regime_engine.classify uses for its own threshold-based checks.
        confidence = min(1.0, max(0.0, ratio / (2 * SUPPORT_RATIO)))
        return AgentOpinion(self.agent_id, stance, confidence, findings)
