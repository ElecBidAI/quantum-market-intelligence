"""What an agent has to analyze.

`candidate` and `risk_decision` are the same dict shapes used everywhere
else in this repo (`strategy_engine.strategy.StrategyCandidate`,
`risk_engine.engine.evaluate()`'s return value) — the council sits
downstream of both, analyzing what already happened, not producing new
market data or re-running the pipeline itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from regime_engine.classify import RegimeResult


@dataclass(frozen=True)
class CouncilContext:
    candidate: dict
    regime: RegimeResult
    risk_decision: dict
    backtest_summary: dict | None = None
    simulation_summary: dict | None = None

    def __post_init__(self) -> None:
        if self.risk_decision["decision"] not in ("APPROVE", "REDUCE", "REJECT"):
            raise ValueError(f"unrecognized risk decision {self.risk_decision['decision']!r}")
