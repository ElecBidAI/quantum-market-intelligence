"""Checks internal consistency and provenance (brief Section 16: "checks formulas,
data provenance, model versions and contradictions").

This is not a re-run of any formula — it checks that the *shape* of what's
already been produced is self-consistent: does the candidate's stated regime
still match the regime the council was actually given (a stale candidate
generated against an earlier classification is exactly the kind of
contradiction this role exists to catch), and do the stop/target prices sit
on the correct side of entry for the stated direction.
"""

from __future__ import annotations

from ai_council.context import CouncilContext
from ai_council.opinion import AgentOpinion, Finding


class Auditor:
    agent_id = "auditor_agent"

    def analyze(self, context: CouncilContext) -> AgentOpinion:
        findings: list[Finding] = []
        candidate = context.candidate
        checks_run = 2  # regime match, strategyId presence — always checked

        if candidate["regime"] != context.regime.label:
            detail = (
                f"candidate regime {candidate['regime']!r} != "
                f"current regime {context.regime.label!r}"
            )
            findings.append(Finding("REGIME_MISMATCH", detail))

        if not candidate.get("strategyId"):
            findings.append(Finding("MISSING_STRATEGY_ID", "candidate has no strategyId"))

        entry = candidate["entryLogic"].get("entryPrice")
        stop = candidate["stopLogic"].get("stopPrice")
        target = candidate["targetLogic"].get("targetPrice")
        prices_present = all(isinstance(v, int | float) for v in (entry, stop, target))
        if prices_present:
            checks_run += 1
            direction = candidate["direction"]
            if direction == "LONG" and not (stop < entry < target):
                detail = (
                    f"LONG requires stop < entry < target; "
                    f"got stop={stop}, entry={entry}, target={target}"
                )
                findings.append(Finding("INCONSISTENT_STOP_TARGET_ORDERING", detail))
            elif direction == "SHORT" and not (target < entry < stop):
                detail = (
                    f"SHORT requires target < entry < stop; "
                    f"got target={target}, entry={entry}, stop={stop}"
                )
                findings.append(Finding("INCONSISTENT_STOP_TARGET_ORDERING", detail))

        stance = "OPPOSE" if findings else "SUPPORT"
        confidence = 1.0 if not findings else len(findings) / checks_run
        return AgentOpinion(self.agent_id, stance, confidence, findings)
