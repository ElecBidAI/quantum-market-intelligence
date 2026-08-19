"""Actively searches for reasons to doubt the candidate (brief Section 16).

Structurally cannot output SUPPORT — its `analyze()` only ever returns
OPPOSE (something looked wrong) or NEUTRAL (nothing did), the same kind of
structural constraint `strategy_engine.engine.run_strategies` uses for the
regime gate: the role isn't trusted to "decide to be skeptical," it's
incapable of endorsing by construction.
"""

from __future__ import annotations

from ai_council.context import CouncilContext
from ai_council.opinion import AgentOpinion, Finding

REGIME_CONFIDENCE_THRESHOLD = 0.5
SIGNAL_STRENGTH_THRESHOLD = 0.3
EDGE_COST_RATIO_THRESHOLD = 1.5
WIN_RATE_THRESHOLD = 0.4


class DevilsAdvocate:
    agent_id = "devils_advocate"

    def analyze(self, context: CouncilContext) -> AgentOpinion:
        findings: list[Finding] = []
        candidate = context.candidate
        checks_run = 3

        regime_confidence = context.regime.confidence
        if regime_confidence < REGIME_CONFIDENCE_THRESHOLD:
            detail = f"regime confidence {regime_confidence:.2f} < {REGIME_CONFIDENCE_THRESHOLD}"
            findings.append(Finding("LOW_REGIME_CONFIDENCE", detail))

        signal_strength = candidate["signalStrength"]
        if signal_strength < SIGNAL_STRENGTH_THRESHOLD:
            detail = f"signalStrength {signal_strength:.2f} < {SIGNAL_STRENGTH_THRESHOLD}"
            findings.append(Finding("WEAK_SIGNAL_STRENGTH", detail))

        costs = candidate["estimatedCosts"]
        if costs > 0:
            ratio = candidate["expectedEdge"] / costs
            if ratio < EDGE_COST_RATIO_THRESHOLD:
                detail = f"edge/cost ratio {ratio:.2f} < {EDGE_COST_RATIO_THRESHOLD}"
                findings.append(Finding("THIN_EDGE_MARGIN", detail))

        summary = context.backtest_summary
        has_win_rate = summary is not None and summary.get("win_rate") is not None
        if has_win_rate:
            checks_run += 1
            win_rate = summary["win_rate"]
            if win_rate < WIN_RATE_THRESHOLD:
                detail = f"win_rate {win_rate:.2f} < {WIN_RATE_THRESHOLD}"
                findings.append(Finding("LOW_HISTORICAL_WIN_RATE", detail))

        stance = "OPPOSE" if findings else "NEUTRAL"
        confidence = len(findings) / checks_run
        return AgentOpinion(self.agent_id, stance, confidence, findings)
