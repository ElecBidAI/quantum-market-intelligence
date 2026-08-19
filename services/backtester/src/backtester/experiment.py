"""Reproducible experiment record (brief Section 17; docs/risk/RISK-GOVERNANCE.md Section 10).

Mirrors the pipeline exactly:

    Hypothesis -> dataset/version -> transformations/features -> formulas/model
    -> parameters -> costs/assumptions -> backtest -> walk-forward -> Monte Carlo
    -> stress tests -> risk review -> conclusion -> status

`monte_carlo_summary`, `stress_test_summary`, and `risk_review` are optional
(default None) because simulation-engine (Phase 5) and a wired-up
risk-engine pipeline (Phases 6-7) don't exist yet — an experiment recorded
today genuinely doesn't have those steps to report, and a None here is
honest about that rather than a placeholder pretending they ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["REJECTED", "RESEARCH", "PAPER", "APPROVED"]
_VALID_STATUSES = ("REJECTED", "RESEARCH", "PAPER", "APPROVED")


@dataclass(frozen=True)
class ExperimentRecord:
    hypothesis: str
    dataset_version: str
    transformations: list[str]
    model_or_formula: str
    parameters: dict[str, Any]
    cost_assumptions: dict[str, Any]
    backtest_summary: dict[str, Any]
    walk_forward_summary: dict[str, Any] | None
    conclusion: str
    status: Status
    monte_carlo_summary: dict[str, Any] | None = None
    stress_test_summary: dict[str, Any] | None = None
    risk_review: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.hypothesis.strip():
            raise ValueError("hypothesis must not be empty")
        if not self.dataset_version.strip():
            raise ValueError("dataset_version must not be empty")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {_VALID_STATUSES}, got {self.status!r}")
        if not self.conclusion.strip():
            raise ValueError("conclusion must not be empty")
