"""QMI transparent scoring (brief Section 15).

`weighted_score` is deliberately generic rather than hard-coding the brief's
named component lists (Opportunity: trend, momentum, volume, liquidity,
microstructure, regime, cross-market confirmation, fundamental/on-chain
evidence, statistical edge; Risk: volatility, tail risk, drawdown, liquidity,
correlation, leverage, event/security risk; Confidence: data quality, model
calibration, model agreement, parameter stability, out-of-sample evidence) —
several of those evidence sources don't exist yet (no microstructure-engine,
no on-chain data, no cross-market correlation infrastructure), so hard-coding
them as required fields would force fake placeholder values into a real
score. The caller supplies whatever normalized (0-100) components it
actually has and a weight for each; this function does not know or care what
the component names mean.

`DEFAULT_*_WEIGHTS` below are placeholders, same caveat as
risk_engine.limits.RiskLimits and regime_engine.thresholds.RegimeThresholds:
not researched or validated, just enough to make the scorer runnable. Brief
Section 15: "Weights must be configurable and validated by strategy/regime.
Do not hard-code an untested universal weighting scheme" — these are
deliberately *not* presented as that scheme, only as one starting point a
caller can override per strategy/regime.
"""

from __future__ import annotations

DEFAULT_OPPORTUNITY_WEIGHTS = {
    "trend": 1.0,
    "momentum": 1.0,
    "volume": 0.5,
    "regime_confidence": 1.0,
    "statistical_edge": 1.5,
}

DEFAULT_RISK_WEIGHTS = {
    "volatility": 1.0,
    "drawdown": 1.0,
    "liquidity_risk": 1.0,
    "leverage": 0.5,
}

DEFAULT_CONFIDENCE_WEIGHTS = {
    "data_quality": 1.0,
    "model_agreement": 1.0,
    "parameter_stability": 0.5,
    "out_of_sample_evidence": 1.5,
}


def weighted_score(components: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted average of `components` (each in [0, 100]) using `weights`, normalized to [0, 100].

    Every key in `components` must have a matching weight — a component
    silently dropped because nobody configured its weight would understate
    the evidence going into the score, which is worse than raising.
    """
    if not components:
        raise ValueError("components must be non-empty")
    for name, value in components.items():
        if not 0 <= value <= 100:
            raise ValueError(f"component {name!r} must be in [0, 100], got {value}")
        if name not in weights:
            raise ValueError(f"no weight configured for component {name!r}")

    total_weight = sum(weights[name] for name in components)
    if total_weight <= 0:
        raise ValueError("sum of weights must be positive")

    return sum(components[name] * weights[name] for name in components) / total_weight


def opportunity_score(
    components: dict[str, float], weights: dict[str, float] | None = None
) -> float:
    return weighted_score(components, weights or DEFAULT_OPPORTUNITY_WEIGHTS)


def risk_score(components: dict[str, float], weights: dict[str, float] | None = None) -> float:
    return weighted_score(components, weights or DEFAULT_RISK_WEIGHTS)


def confidence_score(
    components: dict[str, float], weights: dict[str, float] | None = None
) -> float:
    return weighted_score(components, weights or DEFAULT_CONFIDENCE_WEIGHTS)


def net_edge_score(opportunity: float, risk: float, confidence: float) -> float:
    """NetEdge = Opportunity x (1 - Risk/100) x (Confidence/100) — the brief's formula, verbatim."""
    for name, value in (("opportunity", opportunity), ("risk", risk), ("confidence", confidence)):
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be in [0, 100], got {value}")
    return opportunity * (1 - risk / 100) * (confidence / 100)
