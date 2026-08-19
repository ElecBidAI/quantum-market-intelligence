# regime-engine

Phase 6: rule-based market regime classification (brief Section 7).

`classify.py`'s `classify_regime()` labels a bar series as exactly one of the
eight regimes the brief names as a minimum — `BULLISH_TREND`, `BEARISH_TREND`,
`SIDEWAYS`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`, `ACCUMULATION`,
`DISTRIBUTION`, `STRESS_EVENT` — via a fixed-priority decision tree over SMA
spread (trend), rolling volatility (vol level), OBV trend (accumulation/
distribution), and a return-vs-volatility outlier check (stress, checked
first so it overrides everything else). Every threshold lives in
`thresholds.py`'s `RegimeThresholds`, a placeholder configuration the same
way `risk_engine.limits.RiskLimits` is — runnable now, not calibrated against
real history yet.

`confidence` is a heuristic ("how far past the triggering threshold," via
`_threshold_confidence`), not a statistically fitted probability — see the
module docstring in `classify.py` for why an HMM or similar isn't
implemented instead.

## Not in Phase 6

- No fitted/ML regime model (HMM, etc.) — brief Section 4 lists Hidden Markov
  Models under time series, and this repo has no model-fitting pipeline yet.
- No live wiring to `services/feature-engine` or a `regime_predictions`
  table — `classify_regime()` takes bars directly; nothing runs it on a
  schedule against ingested data yet.

## Tests

Each of the eight labels is exercised with a synthetic bar fixture
engineered to trigger exactly that branch (verified by running the actual
classifier against candidate fixtures until each one landed cleanly — see
the commit history) — not just structural assertions.
